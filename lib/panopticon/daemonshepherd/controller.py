#!/usr/bin/python

import yaml
import daemon
import time
import select

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

class Controller:
  def __init__(self, daemon_spec_file, socket_address = None):
    self.daemon_spec_file = daemon_spec_file
    self.running  = {} # name => daemon.Daemon
    self.expected = {} # name => daemon.Daemon
    self.defaults = {}
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

    for dname in self.running.keys(): # self.running can change in the middle
      daemon = self.running[dname]
      if not daemon.is_alive():
        # close daemon's pipe, in case it was still opened
        # FIXME: this can loose some of the daemon's output
        self.poll.remove(daemon)
        daemon.close()
        # TODO: schedule the restart
        del self.running[dname]

  def loop(self):
    while True:
      self.check_children()
      # TODO: process restart queue
      self.converge()

  #-------------------------------------------------------------------

  def reload(self):
    spec = yaml.safe_load(open(self.daemon_spec_file))
    self.defaults = spec.get('defaults', {})

    def var(daemon, varname):
      if varname in spec['daemons'][daemon]:
        return spec['daemons'][daemon][varname]
      return self.defaults.get(varname)

    self.expected = {}
    for dname in spec['daemons']:
      self.expected[dname] = daemon.Daemon(
        name          = dname,
        start_command = var(dname, 'start_command'),
        stop_command  = var(dname, 'stop_command'),
        stop_signal   = var(dname, 'stop_signal'),
        backoff       = var(dname, 'restart'),
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
        self.expected[daemon].start()
        self.running[daemon] = self.expected[daemon]
        self.poll.add(self.running[daemon])
    for daemon in self.running.keys():
      if daemon not in self.expected:
        self.running[daemon].stop()
        self.poll.remove(self.running[daemon])
        del self.running[daemon]

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
