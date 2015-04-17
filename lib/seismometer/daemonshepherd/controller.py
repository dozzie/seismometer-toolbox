#!/usr/bin/python
'''
Daemon starter and data dispatcher
----------------------------------

.. autoclass:: Controller
   :members:

   .. attribute:: daemon_spec_file

      Name of the file with daemons specification. This file is reloaded on
      ``reload`` command from command channel.

   .. attribute:: restart_queue

      Daemons to restart at appropriate time. :class:`RestartQueue` instance.

   .. attribute:: poll

      Poll object to check for input from command channel or daemons.
      :class:`seismometer.poll.Poll` instance.

   .. attribute:: socket

      Socket on which command channel works.
      :class:`seismometer.daemonshepherd.control_socket.ControlSocket`
      instance.

   .. attribute:: running

      List of currently running daemons. It's a dictionary with mapping
      daemons' names to :class:`seismometer.daemonshepherd.daemon.Daemon`
      instances.

   .. attribute:: expected

      List of daemons that are *expected* to be running. It's a dictionary
      with mapping daemons' names to
      :class:`seismometer.daemonshepherd.daemon.Daemon` instances.

   .. attribute:: start_priorities

      Mapping between daemons' names and their start priorities (lower
      priority starts earlier).

      Only used for starting daemons when booting or reloading config.

   .. attribute:: keep_running

      Marker to terminate :meth:`loop` gracefully from inside of signal
      handlers.

.. autoclass:: RestartQueue
   :members:

'''
#-----------------------------------------------------------------------------

import yaml
import daemon
import time
import heapq
import logging
import control_socket
import signal
import json

import seismometer.poll

#-----------------------------------------------------------------------------

class RestartQueue:
    '''
    Container for daemons to restart.
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

    def add(self, daemon_name, backoff = None):
        '''
        :param daemon_name: name of daemon to add
        :type daemon_name: string
        :param backoff: backoff times (in seconds) for consequent restarts
        :type backoff: list of integers

        Register daemon with its restart strategy.

        If :obj:`backoff` is ``None``, default restart strategy is
        ``[0, 5, 15, 30, 60]``.
        '''
        if backoff is None:
            backoff = [0, 5, 15, 30, 60]
        self.backoff[daemon_name] = backoff
        self.backoff_pos[daemon_name] = 0
        self.restart_time[daemon_name] = None

    # the daemon has just been started (or is going to be in a second)
    def daemon_started(self, name):
        '''
        :param name: daemon that has been started

        Notify restart queue that a daemon has just been started.
        '''
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
        self.restart_time[name] = None
        self.backoff_pos[name] = 0
        logger = logging.getLogger("restart_queue")
        logger.info("daemon %s stopped", name)

    # the daemon has just died
    def daemon_died(self, name):
        '''
        :param name: daemon that has died

        Notify restart queue that a daemon has just died. The queue schedules
        the daemon for restart according to the restart strategy (see
        :meth:`add`).

        List of daemons ready to restart can be retrieved using
        :meth:`restart`.
        '''
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
        logger.warning("daemon %s died, sleeping %d", name, restart_backoff)

        if self.backoff_pos[name] + 1 < len(self.backoff[name]):
            # advance to next backoff on next restart
            self.backoff_pos[name] += 1
        schedule = time.time() + restart_backoff
        heapq.heappush(self.restart_queue, (schedule, name))

    def cancel_restart(self, daemon_name):
        '''
        :param daemon_name: daemon, for which restart is cancelled

        Abort any pending restart of a daemon.
        '''
        # find where in the queue is the daemon placed
        for di in range(len(self.restart_queue)):
            if self.restart_queue[di][1] == daemon_name:
                # this is heap queue, so removing arbitrary element is
                # difficult; let's just leave `None` as a marker
                self.restart_queue[di] = (self.restart_queue[di][0], None)
        self.backoff_pos[daemon_name] = 0
        self.restart_time[daemon_name] = None
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

#-----------------------------------------------------------------------------

class Controller:
    '''
    Daemons and command channel controller.

    The controller responds to commands issued on command channel. Commands
    include reloading daemons specification and listing status of controlled
    daemons. See :meth:`command_*` descriptions for details.
    '''

    def __init__(self, daemon_spec_file, socket_address = None):
        '''
        :param daemon_spec_file: name of the file with daemons specification;
          see :doc:`/commandline/daemonshepherd` for format documentation
        :param socket_address: address of socket for command channel
        '''
        # NOTE: descriptions of attributes moved to top of the module
        self.daemon_spec_file = daemon_spec_file
        self.restart_queue = RestartQueue()
        self.poll = seismometer.poll.Poll()
        if socket_address is not None:
            self.socket = control_socket.ControlSocket(socket_address)
            self.poll.add(self.socket)
        self.running  = {} # name => daemon.Daemon
        self.expected = {} # name => daemon.Daemon
        self.start_priorities = {} # name => int
        self.keep_running = True
        self.reload()
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        '''
        Shutdown the controller along with all the running daemons.
        '''
        logger = logging.getLogger("controller")
        for daemon in self.running.keys():
            logger.info('stopping daemon %s', daemon)
            self.running[daemon].stop()
            self.poll.remove(self.running[daemon])
            del self.running[daemon]

    def check_children(self):
        '''
        Check for output from command channels and daemons, remove daemons
        that died from list of running ones and place them in restart queue.
        '''
        for daemon in self.poll.poll():
            if isinstance(daemon, control_socket.ControlSocket):
                client = daemon.accept()
                self.poll.add(client)
                continue

            if isinstance(daemon, control_socket.ControlSocketClient):
                self.handle_command(daemon)
                continue

            # isinstance(daemon, daemon.Daemon)
            self.handle_daemon_output(daemon)

        # check if all the daemons are still running
        for dname in self.running.keys(): # self.running can change
            daemon = self.running[dname]
            if not daemon.is_alive():
                # close daemon's pipe, in case it was still opened
                # FIXME: this can loose some of the daemon's output
                self.poll.remove(daemon)
                daemon.close()
                del self.running[dname]
                self.restart_queue.daemon_died(dname)

    def loop(self):
        '''
        Main operation loop: check output from daemons or command channels,
        restart daemons that died according to their restart strategy.

        Exits (without stopping children) when :attr:`keep_running` instance
        attribute changes to ``False``.
        '''
        while self.keep_running:
            self.check_children()
            # start all daemons suitable for restart
            for daemon in self.restart_queue.get_restart_ready():
                # TODO: move these four operations to a separate function
                self.restart_queue.daemon_started(daemon)
                self.expected[daemon].start()
                self.running[daemon] = self.expected[daemon]
                self.poll.add(self.running[daemon])

    #-------------------------------------------------------------------

    def signal_handler(self, sig, stack_frame):
        '''
        Signal handler. On *SIGTERM* or *SIGINT* shuts down the controller, on
        *SIGHUP* reloads daemons specification file.
        '''
        logger = logging.getLogger("controller")
        signal_names = dict([
            (signal.__dict__[name], name)
            for name in signal.__dict__
            if name.startswith("SIG") and name not in ("SIG_DFL", "SIG_IGN")
        ])
        signame = signal_names[sig]
        if signame in ("SIGTERM", "SIGINT"):
            logger.info('got signal %s, shutting down', signame)
            self.keep_running = False # let the loop terminate gracefully
        elif signame == "SIGHUP":
            logger.info('got signal %s, reloading config', signame)
            self.reload()
        else:
            logger.warning('got unknown signal %d (%s)', signame, sig)
            pass # or something else?

    #-------------------------------------------------------------------

    def handle_command(self, client):
        '''
        Handle a command from command channel. See :meth:`command_*` methods
        for details on particular commands.
        '''
        cmd = client.read()
        if cmd is None: # EOF
            self.poll.remove(client)
            client.close()
            return

        logger = logging.getLogger("controller")
        if "command" not in cmd:
            logger.warning('unknown command: %s', json.dumps(cmd))
            return

        method_name = "command_%s" % (cmd["command"],)
        if method_name not in self.__class__.__dict__:
            logger.warning('command not implemented: %s', cmd["command"])
            client.send(
                {"status": "error", "message": "command not implemented"}
            )
            return

        # TODO: signal errors: {"status": "error", "reason": "..."}
        # XXX: self.__class__.__dict__ gives unbound methods -- I need to pass
        # `self' manually
        result = self.__class__.__dict__[method_name](self, **cmd)
        if result is None:
            client.send({"status": "ok"})
        else:
            client.send({"status": "ok", "result": result})

    def handle_daemon_output(self, daemon):
        '''
        Handle output from a daemon according to daemon's definition: either
        log it or forward it as a message.
        '''
        line = daemon.readline()
        if line == '': # EOF, but this doesn't mean that the daemon died yet
            self.poll.remove(daemon)
            daemon.close()
        else:
            # TODO: process the line (JSON-decode and forward it or log using
            # logging module)
            pass

    #-------------------------------------------------------------------

    def reload(self):
        '''
        Reload daemon specifications from :attr:`daemon_spec_file` and
        converge list of running daemons with expectations list (see
        :meth:`converge`).

        Method resets the restart queue, trying to start all the missing
        daemons now.
        '''
        logger = logging.getLogger("controller")
        logger.info("reloading configuration from %s", self.daemon_spec_file)

        spec = yaml.safe_load(open(self.daemon_spec_file))
        defaults = spec.get('defaults', {})

        def var(daemon, varname, default = None):
            if varname in spec['daemons'][daemon]:
                return spec['daemons'][daemon][varname]
            return defaults.get(varname, default)

        self.expected = {}
        self.start_priorities = {}
        self.restart_queue.clear()
        for dname in spec['daemons']:
            self.restart_queue.add(dname, var(dname, 'restart'))
            self.start_priorities[dname] = var(dname, 'start_priority', 10)
            self.expected[dname] = daemon.Daemon(
                start_command = var(dname, 'start_command'),
                stop_command  = var(dname, 'stop_command'),
                stop_signal   = var(dname, 'stop_signal'),
                environment   = var(dname, 'environment'),
                cwd           = var(dname, 'cwd'),
                stdout        = var(dname, 'stdout'),
            )
        self.converge()

    def converge(self):
        '''
        Stop the excessive daemons, start missing ones and restart daemons
        which have changed their configuration (command or any of the initial
        environment).
        '''
        logger = logging.getLogger("controller")

        # check for daemons that are running, but have changed commands or
        # environment
        for daemon in self.expected:
            if daemon in self.running and \
               self.expected[daemon] != self.running[daemon]:
                # just stop the changed ones, they'll get started just after
                # this loop
                logger.info("changed config: %s, stopping current instance",
                            daemon)
                self._stop(daemon)

        def prio_cmp(a, b):
            # XXX: self.start_priorities is fully populated with keys from
            # self.expected
            return cmp(self.start_priorities[a], self.start_priorities[b]) or \
                   cmp(a, b)

        # start daemons that are expected to be running but aren't doing so
        for daemon in sorted(self.expected, cmp = prio_cmp):
            if daemon not in self.running:
                logger.info("starting %s", daemon)
                self._start(daemon)

        # stop daemons that are running but are not supposed to
        for daemon in sorted(self.running.keys(), cmp = prio_cmp, reverse = True):
            if daemon not in self.expected:
                # shouldn't be present in self.restart_queue
                logger.info("stopping %s", daemon)
                self._stop(daemon)

    #-------------------------------------------------------------------

    def _stop(self, daemon):
        self.restart_queue.daemon_stopped(daemon)
        self.running[daemon].stop()
        self.poll.remove(self.running[daemon])
        del self.running[daemon]

    def _start(self, daemon):
        self.restart_queue.daemon_started(daemon)
        self.expected[daemon].start()
        self.running[daemon] = self.expected[daemon]
        self.poll.add(self.running[daemon])

    #-------------------------------------------------------------------

    def command_start(self, **kwargs):
        '''
        Start a stopped daemon. If daemon was waiting for restart, it is
        started immediately. Restart backoff is reset in any case.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        if not isinstance(kwargs.get('daemon'), (str, unicode)):
            # TODO: signal error (unrecognized arguments)
            return

        if not kwargs['daemon'] in self.expected:
            # TODO: signal error (unknown daemon)
            return

        logger = logging.getLogger("controller")

        if kwargs['daemon'] not in self.running:
            logger.info("manually starting %s", kwargs['daemon'])
            self._start(kwargs['daemon'])
        self.restart_queue.cancel_restart(kwargs['daemon'])

    #-------------------------------------------------------------------

    def command_stop(self, **kwargs):
        '''
        Start a stopped daemon. If daemon was waiting for restart, its restart
        is cancelled. In either case, restart backoff is reset.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        if not isinstance(kwargs.get('daemon'), (str, unicode)):
            # TODO: signal error (unrecognized arguments)
            return

        if not kwargs['daemon'] in self.expected:
            # TODO: signal error (unknown daemon)
            return

        logger = logging.getLogger("controller")

        if kwargs['daemon'] in self.running:
            logger.info("manually stopping %s", kwargs['daemon'])
            self._stop(kwargs['daemon'])
        self.restart_queue.cancel_restart(kwargs['daemon'])

    #-------------------------------------------------------------------

    def command_restart(self, **kwargs):
        '''
        Restart a daemon. If it was running, it is stopped first. If it was
        waiting for restart or stopped altogether, it is started immediately.
        Restart backoff is reset in any case.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        if not isinstance(kwargs.get('daemon'), (str, unicode)):
            # TODO: signal error (unrecognized arguments)
            return

        if not kwargs['daemon'] in self.expected:
            # TODO: signal error (unknown daemon)
            return

        logger = logging.getLogger("controller")

        if kwargs['daemon'] in self.running:
            logger.info("manually restarting %s", kwargs['daemon'])
            self._stop(kwargs['daemon'])
            self._start(kwargs['daemon'])
        else:
            logger.info("manually restarting %s (was stopped)",
                        kwargs['daemon'])
            self._start(kwargs['daemon'])
        self.restart_queue.cancel_restart(kwargs['daemon'])

    #-------------------------------------------------------------------

    def command_cancel_restart(self, **kwargs):
        '''
        Cancel pending restart of a process. The process stays stopped if it
        was waiting for restart and stays started (with backoff reset) if it
        was started.

        Input data needs to contain ``"daemon"`` key specifying daemon's name.
        '''
        if not isinstance(kwargs.get('daemon'), (str, unicode)):
            # TODO: signal error (unrecognized arguments)
            return

        if not kwargs['daemon'] in self.expected:
            # TODO: signal error (unknown daemon)
            return

        logger = logging.getLogger("controller")

        if kwargs['daemon'] in self.running:
            logger.info("restart cancel for already running %s",
                        kwargs['daemon'])
        else:
            logger.info("restart cancel for awaiting %s", kwargs['daemon'])
        self.restart_queue.cancel_restart(kwargs['daemon'])
        # TODO: return indicator of whether daemon is running or not

    #-------------------------------------------------------------------

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
        restarts = dict([
            (r["name"], r["restart_at"])
            for r in self.restart_queue.list_restarts()
        ])
        # should self.running be included here? probably not, since it's
        # supposed to be a subset of the self.expected
        for name in sorted(self.expected):
            result.append({
                "daemon": name,
                #"command": ..., # TODO: command used to start the daemon
                "pid":     self.expected[name].pid(),
                # there is a small possibility that daemon has just died, so
                # it's not in the restart queue yet (it's basically a race
                # condition); I want here to return a consistent view of the
                # system at some point, so I won't check if the daemon is
                # alive, just if it was supposed to be alive recently
                # (daemon.is_alive() vs. daemon.pid() != None)
                "running": (self.expected[name].pid() is not None),
                "restart_at": restarts.get(name),
            })
        return result

    #-------------------------------------------------------------------

    def command_reload(self, **kwargs):
        '''
        Reload daemon specifications. This command calls :meth:`reload`
        method.
        '''
        self.reload()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
