#!/usr/bin/python

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
  def __init__(self):
    self._poll = select.poll()
    self._object_map = {}

  def add(self, handle):
    if handle.fileno() is None:
      return
    if handle.fileno() in self._object_map:
      return

    # remember for later
    self._object_map[handle.fileno()] = handle
    self._poll.register(handle, select.POLLIN | select.POLLERR)

  def remove(self, handle):
    if handle.fileno() is None:
      return
    if handle.fileno() not in self._object_map:
      return
    del self._object_map[handle.fileno()]
    self._poll.unregister(handle)

  def poll(self, timeout = 100):
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
  def __init__(self):
    self.restart_queue = []
    self.backoff = {}
    self.backoff_pos = {}
    self.restart_time = {}

  def list(self):
    return [{"name": d[1], "restart_at": d[0]} for d in self.restart_queue]

  def clear(self):
    self.restart_queue = []
    self.backoff = {}
    self.backoff_pos = {}
    self.restart_time = {}

  def add(self, daemon_name, backoff = None):
    if backoff is None:
      backoff = [0, 5, 15, 30, 60]
    self.backoff[daemon_name] = backoff
    self.backoff_pos[daemon_name] = 0
    self.restart_time[daemon_name] = None

  # the daemon has just been started (or is going to be in a second)
  def start(self, daemon_name):
    self.restart_time[daemon_name] = time.time()
    logger = logging.getLogger("restart_queue")
    logger.info("daemon %s started", daemon_name)

  # the daemon has just been (intentionally) stopped
  def stop(self, daemon_name):
    # NOTE: unused for now, added for API completeness
    self.restart_time[daemon_name] = None
    self.backoff_pos[daemon_name] = 0
    logger = logging.getLogger("restart_queue")
    logger.info("daemon %s stopped", daemon_name)

  # the daemon has just died
  def die(self, daemon_name):
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
    result = []
    now = time.time()
    while len(self.restart_queue) > 0 and self.restart_queue[0][0] < now:
      (schedule, daemon) = heapq.heappop(self.restart_queue)
      result.append(daemon)
    return result

#-----------------------------------------------------------------------------

class Controller:
  def __init__(self, daemon_spec_file, socket_address = None):
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
    logger = logging.getLogger("controller")
    for daemon in self.running.keys():
      logger.info('stopping daemon %s', daemon)
      self.running[daemon].stop()
      self.poll.remove(self.running[daemon])
      del self.running[daemon]

  def check_children(self):
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
    cmd = client.read()
    if cmd is None: # EOF
      self.poll.remove(client)
      client.close()
      return

    logger = logging.getLogger("controller")
    if "command" not in cmd:
      logger.warning('unknown command: %s', json.dumps(cmd))
      return
    if cmd["command"] == "ps":
      # TODO: be more verbose, e.g. include command used to start the child
      result = {
        "all": sorted(self.expected.keys()),
        "running": sorted(self.running.keys()),
        "awaiting_restart": sorted(self.restart_queue.list()),
      }
      client.send({"status": "ok", "result": result})
    elif cmd["command"] == "start":
      client.send({"status": "todo", "message": "command not implemented"})
      pass
    elif cmd["command"] == "stop":
      client.send({"status": "todo", "message": "command not implemented"})
      pass
    elif cmd["command"] == "restart":
      client.send({"status": "todo", "message": "command not implemented"})
      pass
    elif cmd["command"] == "reload":
      self.reload()
      client.send({"status": "ok"})
    else:
      client.send({"status": "error", "message": "command not implemented"})

  def handle_daemon_output(self, daemon):
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

  def list_processes(self):
    return 

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
