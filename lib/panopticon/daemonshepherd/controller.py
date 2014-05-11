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
      :class:`Poll` instance.

   .. attribute:: socket

      Socket on which command channel works.
      :class:`panopticon.daemonshepherd.control_socket.ControlSocket` instance.

   .. attribute:: running

      List of currently running daemons. It's a dictionary with mapping
      daemons' names to panopticon.daemonshepherd.daemons.Daemons` instances.

   .. attribute:: expected

      List of daemons that are *expected* to be running. It's a dictionary with
      mapping daemons' names to panopticon.daemonshepherd.daemons.Daemons`
      instances.

   .. attribute:: keep_running

      Marker to terminate :meth:`loop` gracefully from inside of signal
      handlers.

.. autoclass:: Poll
   :members:

.. autoclass:: RestartQueue
   :members:

'''
#-----------------------------------------------------------------------------

import yaml
import daemon
import time
import select
import heapq
import logging
import control_socket
import signal
import errno
import json

#-----------------------------------------------------------------------------

class Poll:
  '''
  Convenience wrapper around :mod:`select` module.
  '''

  def __init__(self):
    self._poll = select.poll()
    self._object_map = {}

  def add(self, handle):
    '''
    :param handle: file handle (e.g. :obj:`file` object, but anything with
      :meth:`fileno` method)

    Add a handle to poll list. If ``handle.fileno()`` returns ``None``, the
    handle is not added. The same stands for objects that already were added
    (check is based on file descriptor).
    '''
    if handle.fileno() is None:
      return
    if handle.fileno() in self._object_map:
      return

    # remember for later
    self._object_map[handle.fileno()] = handle
    self._poll.register(handle, select.POLLIN | select.POLLERR)

  def remove(self, handle):
    '''
    :param handle: file handle, the same as for :meth:`add`

    Remove file handle from poll list. Handle must still return valid file
    descriptor on ``handle.fileno()`` call.
    '''
    if handle.fileno() is None:
      return
    if handle.fileno() not in self._object_map:
      return
    del self._object_map[handle.fileno()]
    self._poll.unregister(handle)

  def poll(self, timeout = 100):
    '''
    :param timeout: timeout in milliseconds for *poll* operation
    :return: list of file handles added with :meth:`add` method

    Check whether any data arrives on descriptors. File handles (*handles*,
    not *descriptors*) that are ready for reading are returned as a list.

    Method works around calls interrupted by signals (terminates early instead
    of throwing an exception).
    '''
    try:
      result = self._poll.poll(timeout)
      return [self._object_map[r[0]] for r in result]
    except select.error, e:
      if e.args[0] == errno.EINTR: # in case some signal arrives
        return []
      else: # other error, rethrow
        raise e

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

  def list(self):
    '''
    :return: list of ``{"name": daemon_name, "restart_at": timestamp}`` dicts

    List all daemons scheduled for restart along with their restart times.

    Method intended for queue inspection.
    '''
    return [{"name": d[1], "restart_at": d[0]} for d in self.restart_queue]

  def clear(self):
    '''
    Clear the restart queue, including restart strategies and queued daemons.
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
  def start(self, daemon_name):
    '''
    :param daemon_name: name of daemon that has been started

    Notify restart queue that a daemon has just been started.
    '''
    self.restart_time[daemon_name] = time.time()
    logger = logging.getLogger("restart_queue")
    logger.info("daemon %s started", daemon_name)

  # the daemon has just been (intentionally) stopped
  def stop(self, daemon_name):
    '''
    :param daemon_name: name of daemon that has been stopped

    Notify restart queue that a daemon has just been stopped. Method resets
    backoff time for the daemon.
    '''
    # NOTE: unused for now, added for API completeness
    self.restart_time[daemon_name] = None
    self.backoff_pos[daemon_name] = 0
    logger = logging.getLogger("restart_queue")
    logger.info("daemon %s stopped", daemon_name)

  # the daemon has just died
  def die(self, daemon_name):
    '''
    :param daemon_name: name of daemon that has died

    Notify restart queue that a daemon has just died. The queue schedules the
    daemon for restart according to the restart strategy (see :meth:`add`).

    List of daemons ready to restart can be retrieved using :meth:`restart`.
    '''
    backoff_pos = self.backoff_pos[daemon_name]
    restart_backoff = self.backoff[daemon_name][backoff_pos]
    if restart_backoff < 1: # minimum backoff: 1s
      restart_backoff = 1

    # reset backoff if the command was running long enough (but at least for
    # 10 seconds, to prevent continuous restarts when backoff is small)
    if self.restart_time[daemon_name] is not None:
      running_time = time.time() - self.restart_time[daemon_name]
      if running_time > 10 and running_time > 2 * restart_backoff:
        self.backoff_pos[daemon_name] = 0
        restart_backoff = self.backoff[daemon_name][0]

    logger = logging.getLogger("restart_queue")
    logger.warning("daemon %s died, sleeping %d", daemon_name, restart_backoff)

    if self.backoff_pos[daemon_name] + 1 < len(self.backoff[daemon_name]):
      # advance to next backoff on next restart
      self.backoff_pos[daemon_name] += 1
    schedule = time.time() + restart_backoff
    heapq.heappush(self.restart_queue, (schedule, daemon_name))

  # retrieve list of daemons suitable for restart
  def restart(self):
    '''
    :return: list of names of daemons ready to restart

    List daemons that are ready to restart (the ones for which restart time
    already passed).

    Returned daemons are removed from restart queue.
    '''
    result = []
    now = time.time()
    while len(self.restart_queue) > 0 and self.restart_queue[0][0] < now:
      (schedule, daemon) = heapq.heappop(self.restart_queue)
      result.append(daemon)
    return result

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
    :param daemon_spec_file: name of the file with daemons specification; see
      :doc:`/commandline/daemonshepherd` for format documentation
    :param socket_address: address of socket for command channel
    '''
    # NOTE: descriptions of attributes moved to top of the module
    self.daemon_spec_file = daemon_spec_file
    self.restart_queue = RestartQueue()
    self.poll = Poll()
    if socket_address is not None:
      self.socket = control_socket.ControlSocket(socket_address)
      self.poll.add(self.socket)
    self.running  = {} # name => daemon.Daemon
    self.expected = {} # name => daemon.Daemon
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
    Check for output from command channels and daemons, remove daemons that
    died from list of running ones and place them in restart queue.
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
    for dname in self.running.keys(): # self.running can change in the middle
      daemon = self.running[dname]
      if not daemon.is_alive():
        # close daemon's pipe, in case it was still opened
        # FIXME: this can loose some of the daemon's output
        self.poll.remove(daemon)
        daemon.close()
        del self.running[dname]
        self.restart_queue.die(dname)

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
      for daemon in self.restart_queue.restart():
        # TODO: move these four operations to a separate function
        self.restart_queue.start(daemon)
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
      self.keep_running = False # let the loop terminate itself gracefully
    elif signame == "SIGHUP":
      logger.info('got signal %s, reloading config', signame)
      self.reload()
    else:
      logger.warning('got unknown signal %d (%s)', signame, sig)
      pass # or something else?

  #-------------------------------------------------------------------

  def handle_command(self, client):
    '''
    Handle a command from command channel. See :meth:`command_*` methods for
    details on particular commands.
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
      client.send({"status": "error", "message": "command not implemented"})
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
    Handle output from a daemon according to daemon's definition: either log
    it or send to Streem as a message.
    '''
    line = daemon.readline()
    if line == '': # EOF, but this doesn't mean that the daemon died yet
      self.poll.remove(daemon)
      daemon.close()
    else:
      # TODO: process the line (JSON-decode and send to Streem or log using
      # logging module)
      pass

  #-------------------------------------------------------------------

  def reload(self):
    '''
    Reload daemon specifications from :attr:`daemon_spec_file` and converge
    list of running daemons with expectations list (see :meth:`converge`).

    Method resets the restart queue, trying to start all the missing daemons
    now.
    '''
    logger = logging.getLogger("controller")
    logger.info("reloading configuration from %s", self.daemon_spec_file)

    spec = yaml.safe_load(open(self.daemon_spec_file))
    defaults = spec.get('defaults', {})

    def var(daemon, varname):
      if varname in spec['daemons'][daemon]:
        return spec['daemons'][daemon][varname]
      return defaults.get(varname)

    self.expected = {}
    self.restart_queue.clear()
    for dname in spec['daemons']:
      self.restart_queue.add(dname, var(dname, 'restart'))
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
    Stop the excessive daemons, start missing ones and restart daemons which
    have changed their configuration (command or any of the initial
    environment).
    '''
    logger = logging.getLogger("controller")

    # check for daemons that are running, but have changed commands or
    # environment
    for daemon in self.expected:
      if daemon in self.running and \
         self.expected[daemon] != self.running[daemon]:
        # just stop the changed ones, they'll get started just after this loop
        logger.info("changed config: %s, stopping current instance", daemon)
        self.running[daemon].stop()
        self.poll.remove(self.running[daemon])
        del self.running[daemon]

    # start daemons that are expected to be running but aren't doing so
    for daemon in self.expected:
      if daemon not in self.running:
        logger.info("starting %s", daemon)
        self.restart_queue.start(daemon)
        self.expected[daemon].start()
        self.running[daemon] = self.expected[daemon]
        self.poll.add(self.running[daemon])

    # stop daemons that are running but are not supposed to
    for daemon in self.running.keys():
      if daemon not in self.expected:
        # shouldn't be present in self.restart_queue
        logger.info("stopping %s", daemon)
        self.running[daemon].stop()
        self.poll.remove(self.running[daemon])
        del self.running[daemon]

  #-------------------------------------------------------------------

  def command_ps(self, **kwargs):
    '''
    List daemons that are expected, running and that stay in restart queue.

    Example of returned data::

       {
         "all": ["daemon1", "daemon2"],
         "running": ["daemon2"],
         "awaiting_restart": ["daemon1"]
       }
    '''
    # TODO: be more verbose, e.g. include command used to start the child
    return {
      "all": sorted(self.expected.keys()),
      "running": sorted(self.running.keys()),
      "awaiting_restart": sorted(self.restart_queue.list()),
    }

  def command_reload(self, **kwargs):
    '''
    Reload daemon specifications. This command calls :meth:`reload` method.
    '''
    self.reload()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
