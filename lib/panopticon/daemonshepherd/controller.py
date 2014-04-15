#!/usr/bin/python

import yaml
import daemon
import time
import select
import heapq

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
    result = self._poll.poll(timeout)
    return [self._object_map[r[0]] for r in result]

#-----------------------------------------------------------------------------

class RestartQueue:
  def __init__(self):
    self.restart_queue = []
    self.backoff = {}
    self.backoff_pos = {}
    self.restart_time = {}

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

  # the daemon has just been (intentionally) stopped
  def stop(self, daemon_name):
    # NOTE: unused for now, added for API completeness
    self.restart_time[daemon_name] = None
    self.backoff_pos[daemon_name] = 0

  # the daemon has just died
  def die(self, daemon_name):
    backoff_pos = self.backoff_pos[daemon_name]
    restart_backoff = self.backoff[daemon_name][backoff_pos]

    # reset backoff if the command was running long enough (but at least for
    # 10 seconds, to prevent continuous restarts when backoff == 0)
    if self.restart_time[daemon_name] is not None:
      running_time = time.time() - self.restart_time[daemon_name]
      if running_time > 10 and running_time > 2 * restart_backoff:
        self.backoff_pos[daemon_name] = 0
        restart_backoff = self.backoff[daemon_name][0]

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
    self.running  = {} # name => daemon.Daemon
    self.expected = {} # name => daemon.Daemon
    self.restart_queue = RestartQueue()
    self.poll = Poll()
    self.reload()

  def __del__(self):
    self.shutdown()

  def shutdown(self):
    for daemon in self.running.keys():
      self.running[daemon].stop()
      self.poll.remove(self.running[daemon])
      del self.running[daemon]

  def check_children(self):
    # read daemons' outputs
    for daemon in self.poll.poll():
      line = daemon.readline()
      if line == '':
        # EOF, but this doesn't mean that the daemon died yet
        self.poll.remove(daemon)
        daemon.close()
      else:
        # TODO: process the line (JSON-decode and send to Streem or log using
        # logging module)
        pass

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
    while True:
      self.check_children()
      # start all daemons suitable for restart
      for daemon in self.restart_queue.restart():
        # TODO: move these four operations to a separate function
        self.restart_queue.start(daemon)
        self.expected[daemon].start()
        self.running[daemon] = self.expected[daemon]
        self.poll.add(self.running[daemon])

  #-------------------------------------------------------------------

  def reload(self):
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
    # stop excessive, start missing daemons
    # TODO: restart processes with changed commands
    for daemon in self.expected:
      if daemon not in self.running:
        self.restart_queue.start(daemon)
        self.expected[daemon].start()
        self.running[daemon] = self.expected[daemon]
        self.poll.add(self.running[daemon])
    for daemon in self.running.keys():
      if daemon not in self.expected:
        # shouldn't be present in self.restart_queue
        self.running[daemon].stop()
        self.poll.remove(self.running[daemon])
        del self.running[daemon]

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
