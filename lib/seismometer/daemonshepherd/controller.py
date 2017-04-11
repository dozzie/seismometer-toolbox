#!/usr/bin/python
'''
Daemon starter and data dispatcher
----------------------------------

.. autoclass:: Controller
   :members:

   Available attributes:

   .. attribute:: load_config

      Zero-argument function that loads daemons specification file and returns
      a dictionary with keys being daemons' names and values being daemons'
      parameters. This function is called on ``reload`` command from command
      channel.

   .. attribute:: restart_queue

      Daemons to restart at appropriate time. :class:`RestartQueue` instance.

   .. attribute:: poll

      Poll object to check for input from command channel or daemons.
      :class:`seismometer.poll.Poll` instance.

   .. attribute:: daemons

      Dictionary with all defined daemons (running, waiting for restart, and
      stopped). Keys are daemons' names and values are
      :class:`seismometer.daemonshepherd.daemon.Daemon` instances.

   .. attribute:: socket

      Socket on which command channel works.
      :class:`seismometer.daemonshepherd.control_socket.ControlSocket`
      instance.

   .. attribute:: keep_running

      Marker to terminate :meth:`loop()` gracefully from inside of signal
      handlers.

.. autoclass:: RestartQueue
   :members:

.. autodata:: DEFAULT_BACKOFF

'''
#-----------------------------------------------------------------------------

import daemon
import time
import heapq
import logging
import control_socket
import filehandle
import signal
import json
import os

import seismometer.poll

#-----------------------------------------------------------------------------

DEFAULT_BACKOFF = [0, 5, 15, 30, 60]
'''
List of backoff times for default restart strategy.
'''

SIGNAL_NAMES = dict([
    (signal.__dict__[name], name)
    for name in signal.__dict__
    if name.startswith("SIG") and name != "SIG_DFL" and name != "SIG_IGN"
])

#-----------------------------------------------------------------------------
# RestartQueue {{{

class RestartQueue:
    '''
    Schedule for daemon restarts.
    '''

    def __init__(self):
        self.restart_queue = []
        self.backoff = {}
        self.backoff_pos = {}
        self.restart_time = {}

    def list_restarts(self):
        '''
        :return: list of ``{"name": daemon_name, "restart_at": timestamp}``
            dicts

        List all daemons scheduled for restart along with their restart times.

        Method intended for queue inspection.
        '''
        return [
            {"name": d[1], "restart_at": d[0]}
            for d in self.restart_queue
            if d[1] is not None
        ]

    def clear(self):
        '''
        Clear the restart queue, including restart strategies and queued
        daemons.
        '''
        self.restart_queue = []
        self.backoff = {}
        self.backoff_pos = {}
        self.restart_time = {}

    def add(self, daemon_name, backoff):
        '''
        :param daemon_name: name of daemon to add
        :type daemon_name: string
        :param backoff: backoff times (in seconds) for consequent restarts
        :type backoff: list of integers

        Register daemon with its restart strategy.
        '''
        self.backoff[daemon_name] = backoff
        self.backoff_pos[daemon_name] = 0
        self.restart_time[daemon_name] = None

    def remove(self, daemon_name):
        '''
        :param daemon_name: name of daemon to remove
        :type daemon_name: string

        Unregister daemon from the queue.
        '''
        if name not in self.backoff:
            return # ignore unknown daemons

        self.cancel_restart(daemon_name)
        del self.backoff[daemon_name]
        del self.backoff_pos[daemon_name]
        del self.restart_time[daemon_name]

    # the daemon has just been started (or is going to be in a second)
    def daemon_started(self, name):
        '''
        :param name: daemon that has been started

        Notify restart queue that a daemon has just been started.
        '''
        if name not in self.backoff:
            return # ignore unknown daemons

        self.restart_time[name] = time.time()
        logger = logging.getLogger("restart_queue")
        logger.info("daemon %s started", name)

    # the daemon has just been (intentionally) stopped
    def daemon_stopped(self, name):
        '''
        :param name: daemon that has been stopped

        Notify restart queue that a daemon has just been stopped. Method
        resets backoff time for the daemon.
        '''
        if name not in self.backoff:
            return # ignore unknown daemons

        self.restart_time[name] = None
        self.backoff_pos[name] = 0
        logger = logging.getLogger("restart_queue")
        logger.info("daemon %s stopped", name)

    # the daemon has just died
    def daemon_died(self, name, exit_code = None, signame = None):
        '''
        :param name: daemon that has died
        :param exit_code: exit code of the daemon or ``None`` if it died on
            signal
        :param signame: signal name that terminated the daemon or ``None`` if
            the daemon exited

        Notify restart queue that a daemon has just died. The queue schedules
        the daemon for restart according to the restart strategy (see
        :meth:`add()`).

        List of daemons ready to restart can be retrieved using
        :meth:`restart()`.
        '''
        if name not in self.backoff:
            return # ignore unknown daemons

        backoff_pos = self.backoff_pos[name]
        restart_backoff = self.backoff[name][backoff_pos]
        if restart_backoff < 1: # minimum backoff: 1s
            restart_backoff = 1

        # reset backoff if the command was running long enough (but at least
        # for 10 seconds, to prevent continuous restarts when backoff is
        # small)
        if self.restart_time[name] is not None:
            running_time = time.time() - self.restart_time[name]
            if running_time > 10 and running_time > 2 * restart_backoff:
                self.backoff_pos[name] = 0
                restart_backoff = self.backoff[name][0]

        logger = logging.getLogger("restart_queue")
        if exit_code is None and signame is None:
            logger.warning("daemon %s died, sleeping %d",
                           name, restart_backoff)
        elif exit_code is not None:
            logger.warning("daemon %s exited with code %d, sleeping %d",
                           name, exit_code, restart_backoff)
        else: # signame is not None
            logger.warning("daemon %s died on signal %s, sleeping %d",
                           name, signame, restart_backoff)

        if self.backoff_pos[name] + 1 < len(self.backoff[name]):
            # advance to next backoff on next restart
            self.backoff_pos[name] += 1
        schedule = time.time() + restart_backoff
        heapq.heappush(self.restart_queue, (schedule, name))

    def cancel_restart(self, name):
        '''
        :param name: daemon, for which restart is cancelled

        Abort any pending restart of a daemon.
        '''
        if name not in self.backoff:
            return # ignore unknown daemons

        # find where in the queue is the daemon placed
        for di in range(len(self.restart_queue)):
            if self.restart_queue[di][1] == name:
                # this is heap queue, so removing arbitrary element is
                # difficult; let's just leave `None` as a marker
                self.restart_queue[di] = (self.restart_queue[di][0], None)
        self.backoff_pos[name] = 0
        self.restart_time[name] = None
        self._remove_cancelled()

    # retrieve list of daemons suitable for restart
    def get_restart_ready(self):
        '''
        :return: list of names of daemons ready to restart

        List daemons that are ready to restart (the ones for which restart
        time already passed).

        Returned daemons are removed from restart queue.
        '''
        result = []
        now = time.time()
        while len(self.restart_queue) > 0 and self.restart_queue[0][0] < now:
            (schedule, daemon) = heapq.heappop(self.restart_queue)
            if daemon is not None: # could be a cancelled restart
                result.append(daemon)
        self._remove_cancelled()
        return result

    def _remove_cancelled(self):
        # remove cancelled restarts from the head of the queue
        while len(self.restart_queue) > 0 and self.restart_queue[0][1] is None:
            heapq.heappop(self.restart_queue)

# }}}
#-----------------------------------------------------------------------------

class Controller:
    '''
    Daemons and command channel controller.

    The controller responds to commands issued on command channel. Commands
    include reloading daemons specification and listing status of controlled
    daemons. See :meth:`command_*()` descriptions for details.
    '''

    def __init__(self, load_config, socket_address = None):
        '''
        :param load_config: function that loads the file with daemons
            specification; see :doc:`/manpages/daemonshepherd` for format
            documentation
        :param socket_address: address of socket for command channel
        '''
        # NOTE: descriptions of attributes moved to top of the module
        self.load_config = load_config
        self.restart_queue = RestartQueue()
        self.poll = seismometer.poll.Poll()
        self.daemons = {} # name => daemon.Daemon
        # daemons' metadata:
        #   "name": string
        #   "running": True | False
        #   "start_priority": integer
        #   "restart": list of integers

        self.keep_running = True
        if socket_address is not None:
            self.socket = control_socket.ControlSocket(socket_address)
            self.poll.add(self.socket)
        else:
            self.socket = None
        signal.signal(signal.SIGHUP, self.signal_reload)
        signal.signal(signal.SIGINT, self.signal_shutdown)
        signal.signal(signal.SIGTERM, self.signal_shutdown)
        signal.signal(signal.SIGCHLD, self.signal_child_died)
        if not self.reload():
            raise Exception("configuration loading error")

    def __del__(self):
        self.shutdown()

    #-------------------------------------------------------------------
    # child daemon management: _start(), _stop(), _died() {{{

    def _stop(self, name):
        self.restart_queue.daemon_stopped(name)
        self.poll.remove(self.daemons[name])
        # FIXME: this can loose some of the daemon's output
        self.daemons[name].stop()
        self.daemons[name]["running"] = False

    def _died(self, name, exit_code = None, signame = None):
        self.restart_queue.daemon_died(name, exit_code, signame)
        self.poll.remove(self.daemons[name])
        # FIXME: this can loose some of the daemon's output
        self.daemons[name].reap()
        self.daemons[name]["running"] = False

    def _start(self, name):
        self.restart_queue.daemon_started(name)
        self.daemons[name].start()
        self.daemons[name]["running"] = True
        self.poll.add(self.daemons[name])

    # }}}
    #-------------------------------------------------------------------
    # signal handlers {{{

    def signal_shutdown(self, signum, stack_frame):
        '''
        Signal handler that shuts down the controller.
        '''
        logger = logging.getLogger("controller")
        signame = SIGNAL_NAMES.get(signum, str(signum))
        logger.info("got signal %s, shutting down", signame)
        self.keep_running = False # let the loop terminate gracefully

    def signal_reload(self, signum, stack_frame):
        '''
        Signal handler that reloads daemons specification file.
        '''
        logger = logging.getLogger("controller")
        signame = SIGNAL_NAMES.get(signum, str(signum))
        logger.info("got signal %s, reloading config", signame)
        self.reload()

    def signal_child_died(self, signum, stack_frame):
        '''
        *SIGCHLD* signal handler to mark dead children and put them to the
        restart queue.
        '''
        logger = logging.getLogger("controller")

        while True:
            # reap all the terminated children
            try:
                (pid, status) = os.waitpid(-1, os.WNOHANG)
            except OSError:
                return # ECHILD errno, no more children
            if pid == 0:
                return # there are some children, but none has terminated

            if os.WIFEXITED(status):
                exit_code = os.WEXITSTATUS(status)
                signame = None
            else: # os.WIFSIGNALED(status)
                exit_code = None
                signum = os.WTERMSIG(status)
                signame = SIGNAL_NAMES.get(signum, str(signum))

            # FIXME: this is quite ineffective search, but should be good
            # enough for now (also, list of supervised daemons should be quite
            # short)
            handle = None
            for name in self.daemons:
                if self.daemons[name].pid() == pid:
                    handle = self.daemons[name]
                    break

            if handle is not None:
                self._died(handle["name"], exit_code, signame)
            elif exit_code is not None:
                logger.warning("untracked child PID=%d exited with code %d",
                               pid, exit_code)
            else:
                logger.warning("untracked child PID=%d died on signal %s",
                               pid, signame)

    # }}}
    #-------------------------------------------------------------------

    def shutdown(self):
        '''
        Shutdown the controller along with all the running daemons.
        '''
        for name in self.daemons.keys():
            self._stop(name)
            del self.daemons[name]
        self.restart_queue.clear()
        # delete self.poll entries?

    def loop(self):
        '''
        Main operation loop: check output from daemons or command channels,
        restart daemons that died according to their restart strategy.

        Returns when :attr:`keep_running` instance attribute changes to
        ``False``, but does not stop its children. To do this use
        :meth:`shutdown()`.
        '''
        while self.keep_running:
            for handle in self.poll.poll(timeout = 100):
                if isinstance(handle, control_socket.ControlSocket):
                    client = handle.accept()
                    self.poll.add(client)
                elif isinstance(handle, control_socket.ControlSocketClient):
                    command = handle.read()
                    if command is filehandle.EOF:
                        self.poll.remove(handle)
                        handle.close()
                    else:
                        self.handle_command(command, handle)
                else: # isinstance(handle, daemon.Daemon)
                    self.handle_daemon_output(handle)
            # process due restarts
            for name in self.restart_queue.get_restart_ready():
                self._start(name)

    #-------------------------------------------------------------------
    # handle_command() {{{

    def handle_command(self, command, client):
        '''
        :param command: dictionary with command to execute
        :param client: :class:`control_socket.ControlSocketClient` to send
            response to

        Handle a command from command channel. See :meth:`command_*()` methods
        for details on particular commands.
        '''
        logger = logging.getLogger("controller")
        if "command" not in command or \
           not isinstance(command["command"], (str, unicode)):
            logger.warning("unknown command: %s", json.dumps(command))
            return

        method = getattr(self, "command_" + command["command"], None)
        if method is None:
            logger.warning("command not implemented: %s", command["command"])
            client.send(
                {"status": "error", "message": "command not implemented"}
            )
            return

        try:
            # TODO: signal errors: {"status": "error", "reason": "..."}
            result = method(**command)
        except:
            logger.exception("exception in running command %s",
                             command["command"])
            return

        try:
            if result is None:
                client.send({"status": "ok"})
            else:
                client.send({"status": "ok", "result": result})
        except IOError, e:
            pass # TODO: maybe log this exception?

    # }}}
    #-------------------------------------------------------------------
    # handle_daemon_output() {{{

    def handle_daemon_output(self, handle):
        '''
        Handle output from a daemon according to daemon's definition: read it
        all and log it.
        '''
        daemon_logger = logging.getLogger("daemon." + handle["name"])
        line = handle.readline()
        while line is not None and line is not filehandle.EOF:
            daemon_logger.info(line.rstrip("\n"))
            line = handle.readline()

        if line is filehandle.EOF:
            # it's perfectly OK for daemon not to use its STDOUT/STDERR,
            # closing it doesn't mean that the daemon has died
            self.poll.remove(handle)
            handle.close()

    # }}}
    #-------------------------------------------------------------------

    def reload(self):
        '''
        :return: ``True`` when reload was successful, ``False`` on error

        Reload daemon specifications from configuration and converge list of
        running daemons with expectations list.

        Method resets the restart queue, trying to start all the missing
        daemons now.
        '''
        logger = logging.getLogger("controller")
        logger.info("reloading configuration")

        try:
            specs = self.load_config()
        except:
            logger.exception("error when loading config file")
            return False
        if not isinstance(specs, dict):
            logger.error("config loading returned invalid data type")
            return False

        # just daemon names
        daemons_to_stop = [name for name in self.daemons if name not in specs]

        # name => daemon.Daemon
        daemons_to_start = {}
        daemons_to_restart = {}
        daemons_to_update = {}
        for (name, spec) in specs.iteritems():
            # TODO: intercept daemon building errors
            handle = daemon.build(spec)
            handle["name"] = name
            handle["running"] = False
            handle["restart"] = spec.get("restart", DEFAULT_BACKOFF)
            handle["start_priority"] = spec.get("start_priority", 10)
            if name not in self.daemons:
                daemons_to_start[name] = handle
            elif handle != self.daemons[name]:
                daemons_to_restart[name] = handle
            else: # handle == self.daemons[name]
                # NOTE: daemons could be updated here, but I'd rather do it
                # after processing data from config file is finished
                daemons_to_update[name] = handle

        for (name, handle) in daemons_to_update.iteritems():
            # update daemons' metadata coming from config with new values
            self.daemons[name]["restart"] = handle["restart"]
            self.daemons[name]["start_priority"] = handle["start_priority"]
            self.daemons[name].replace_commands(handle)

        def priority_cmp(a, b):
            return cmp(a["start_priority"], b["start_priority"]) or \
                   cmp(a["name"], b["name"])

        for name in sorted(daemons_to_stop):
            logger.info("stopping %s", name)
            self.restart_queue.remove(name)
            self._stop(name)
            del self.daemons[name]

        # repopulate the restart queue anew, so it doesn't accumulate cruft
        # over time; a side effect is resetting all positions in strategies
        self.restart_queue.clear()
        for (name, handle) in daemons_to_start.iteritems():
            self.restart_queue.add(name, handle["restart"])
        for (name, handle) in self.daemons.iteritems():
            # NOTE: some daemons will be added twice, but the later data wins,
            # and we don't know here which daemons_to_restart have different
            # restart strategy
            self.restart_queue.add(name, handle["restart"])
        for (name, handle) in daemons_to_restart.iteritems():
            self.restart_queue.add(name, handle["restart"])

        # NOTE: restarting has _an_ order, not some specific one; this one
        # just happens to be easy to use
        recent_priority = None
        for handle in sorted(daemons_to_restart.values(), cmp = priority_cmp):
            logger.info("changed definition of %s, stopping current instance",
                        handle["name"])
            self._stop(handle["name"])
            logger.info("starting %s", handle["name"])
            self.daemons[handle["name"]] = handle
            self._start(handle["name"])
            if recent_priority != handle["start_priority"]:
                time.sleep(0.1) # delay between different priorities
                recent_priority = handle["start_priority"]

        recent_priority = None
        for handle in sorted(daemons_to_start.values(), cmp = priority_cmp):
            logger.info("starting %s", handle["name"])
            self.daemons[handle["name"]] = handle
            self._start(handle["name"])
            if recent_priority != handle["start_priority"]:
                # FIXME: how should daemon signal that it has started
                # successfully and we can move to starting other daemons?
                time.sleep(0.1) # delay between different priorities
                recent_priority = handle["start_priority"]

        # and this is for all the daemons from the restart queue that we
        # forgot about
        for handle in self.daemons.values():
            if not handle["running"]:
                logger.info("starting %s", handle["name"])
                self.daemons[handle["name"]] = handle
                self._start(handle["name"])

        # report that loading and parsing config was generally successful
        return True

    #-------------------------------------------------------------------
    # command_start(daemon) {{{

    def command_start(self, **kwargs):
        '''
        Start a stopped daemon. If daemon was waiting for restart, it is
        started immediately. Restart backoff is reset in any case.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        name = kwargs.get("daemon")
        if not isinstance(name, (str, unicode)):
            return # TODO: signal error (unrecognized arguments)

        handle = self.daemons.get(name)
        if handle is None:
            return # TODO: signal error (unknown daemon)

        logger = logging.getLogger("controller")

        if not handle["running"]:
            logger.info("manually starting %s", name)
            self._start(name)
        self.restart_queue.cancel_restart(name)

    # }}}
    #-------------------------------------------------------------------
    # command_stop(daemon) {{{

    def command_stop(self, **kwargs):
        '''
        Start a stopped daemon. If daemon was waiting for restart, its restart
        is cancelled. In either case, restart backoff is reset.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        name = kwargs.get("daemon")
        if not isinstance(name, (str, unicode)):
            return # TODO: signal error (unrecognized arguments)

        handle = self.daemons.get(name)
        if handle is None:
            return # TODO: signal error (unknown daemon)

        logger = logging.getLogger("controller")

        if handle["running"]:
            logger.info("manually stopping %s", name)
            self._stop(name)
        self.restart_queue.cancel_restart(name)

    # }}}
    #-------------------------------------------------------------------
    # command_restart(daemon) {{{

    def command_restart(self, **kwargs):
        '''
        Restart a daemon. If it was running, it is stopped first. If it was
        waiting for restart or stopped altogether, it is started immediately.
        Restart backoff is reset in any case.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        name = kwargs.get("daemon")
        if not isinstance(name, (str, unicode)):
            return # TODO: signal error (unrecognized arguments)

        handle = self.daemons.get(name)
        if handle is None:
            return # TODO: signal error (unknown daemon)

        logger = logging.getLogger("controller")

        if handle["running"]:
            logger.info("manually restarting %s", name)
            self._stop(name)
            self._start(name)
        else:
            logger.info("manually restarting %s (was stopped)", name)
            self._start(name)
        self.restart_queue.cancel_restart(name)

    # }}}
    #-------------------------------------------------------------------
    # command_cancel_restart(daemon) {{{

    def command_cancel_restart(self, **kwargs):
        '''
        Cancel pending restart of a process. The process stays stopped if it
        was waiting for restart and stays started (with backoff reset) if it
        was started.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        name = kwargs.get("daemon")
        if not isinstance(name, (str, unicode)):
            return # TODO: signal error (unrecognized arguments)

        handle = self.daemons.get(name)
        if handle is None:
            return # TODO: signal error (unknown daemon)

        logger = logging.getLogger("controller")

        if handle["running"]:
            logger.info("restart cancel for already running %s", name)
        else:
            logger.info("restart cancel for awaiting %s", name)
        self.restart_queue.cancel_restart(name)
        # TODO: return indicator of whether daemon is running or not

    # }}}
    #-------------------------------------------------------------------
    # command_ps() {{{

    def command_ps(self, **kwargs):
        '''
        List daemons that are expected, running and that stay in restart
        queue.

        Returned data is a list of elements of following dictionaries::

           {
             "daemon": <name>,
             "pid": <PID> | None,
             "running": True | False,
             "restart_at": None | <timestamp>
           }
        '''
        result = []
        # XXX: there is a small possibility that a daemon will die just after
        # we build restarts dictionary, so it's not in the restart queue yet;
        # it's basically a race condition
        restarts = dict([
            (r["name"], r["restart_at"])
            for r in self.restart_queue.list_restarts()
        ])
        for name in sorted(self.daemons):
            # XXX: I want here to return a consistent(ish) view of the
            # daemon's state at some point, so I won't check if the daemon is
            # alive, just if it was supposed to be alive recently
            # (daemon.is_alive() vs. daemon.pid() != None)
            pid = self.daemons[name].pid()
            result.append({
                "daemon": name,
                #"command": ..., # TODO: command used to start the daemon
                "pid": pid,
                "running": (pid is not None),
                "restart_at": restarts.get(name),
            })
        return result

    # }}}
    #-------------------------------------------------------------------
    # command_reload() {{{

    def command_reload(self, **kwargs):
        '''
        Reload daemon specifications. This command calls :meth:`reload()`
        method.
        '''
        # TODO: return reload errors
        self.reload()

    # }}}
    #-------------------------------------------------------------------
    # command_admin_command() {{{

    def command_admin_command(self, **kwargs):
        '''
        Run an administrative command.
        '''
        name = kwargs.get("daemon")
        if not isinstance(name, (str, unicode)):
            return # TODO: signal error (unrecognized arguments)

        command = kwargs.get("admin_command")
        if not isinstance(command, (str, unicode)):
            return # TODO: signal error (unrecognized arguments)

        handle = self.daemons.get(name)
        if handle is None:
            return # TODO: signal error (unknown daemon)

        if not handle.has_command(command):
            return # TODO: signal error (unknown command)

        logger = logging.getLogger("controller")

        logger.info("for daemon %s running command %s", name, command)
        handle.command(command)

    # }}}
    #-------------------------------------------------------------------

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
