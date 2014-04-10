#!/usr/bin/python

import pykka
import yaml
import daemon

#-----------------------------------------------------------------------------

class ControllerThread(pykka.ThreadingActor):
  def __init__(self, daemon_spec_file):
    super(ControllerThread, self).__init__()
    self.daemon_spec_file = daemon_spec_file
    self.running  = {} # name => daemon.Daemon
    self.expected = {} # name => daemon.Daemon
    self.defaults = {}

  def on_stop(self):
    for daemon in self.running.keys(): # must be .keys(), since hash changes
      self.running[daemon].stop()
      del self.running[daemon]

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
    # TODO: restart changed
    for daemon in self.expected:
      if daemon not in self.running:
        self.expected[daemon].start()
        self.running[daemon] = self.expected[daemon]
    for daemon in self.running.keys():
      if daemon not in self.expected:
        self.running[daemon].stop()
        del self.running[daemon]

  def start_daemon(self, daemon):
    # NOTE: look in self.expected
    pass

  def stop_daemon(self, daemon):
    # NOTE: look in self.running (and check in self.expected if already
    # stopped)
    pass

#-----------------------------------------------------------------------------

class Controller:
  def __init__(self, daemon_spec_file, socket_address = None):
    self.thread = ControllerThread.start(daemon_spec_file).proxy()
    self.thread.reload()
    # TODO: create socket (TCP/UNIX)

  def __del__(self):
    self.thread.actor_ref.stop()

  def shutdown():
    # TODO: implement me
    pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
