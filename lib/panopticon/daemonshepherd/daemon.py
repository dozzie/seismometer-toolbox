#!/usr/bin/python

import subprocess
import pykka
import time

#-----------------------------------------------------------------------------

class DaemonSupervisor(pykka.ThreadingActor):
  def __init__(self, command, environment, cwd, stdout, backoff):
    super(DaemonSupervisor, self).__init__()
    self.command = command
    self.environment = environment
    self.cwd = cwd
    self.stdout = stdout
    self.backoff = backoff
    self.backoff_position = None
    self.child = None

  def start_child(self):
    # TODO: run self.command to start child

    # XXX: enter child monitoring loop
    self.actor_ref.ask({"monitor": True}, block = False)
    pass

  def stop_child(self, command):
    # TODO: run command to stop child
    pass

  def kill_child(self, signal):
    # TODO: send signal to child
    pass

  def on_receive(self, message):
    # TODO: detect death of the child
    # TODO: read something from child's STDOUT (timeout 100ms)

    print "## <%s> got %s" % (self.command, message)
    time.sleep(2)

    # XXX: loop (somewhat indirect)
    self.actor_ref.ask(message, block = False)

#-----------------------------------------------------------------------------

class Daemon:
  def __init__(self, start_command, stop_command = None, stop_signal = None,
               backoff = None, environment = None, cwd = None, stdout = None):
    if stop_signal is None:
      stop_signal = 15
    # TODO: convert stop_signal from name to number

    self.start_command = start_command
    self.stop_command  = stop_command
    self.stop_signal   = stop_signal

    self.backoff = backoff
    self.environment = environment
    self.cwd = cwd
    self.stdout = stdout

    self.supervisor = DaemonSupervisor.start(
      start_command, environment, self.cwd, self.stdout, backoff,
    ).proxy()

  def __del__(self):
    self.stop()

  def start(self):
    self.supervisor.start_child().get()

  def stop(self):
    if self.supervisor.actor_ref.is_alive():
      if self.stop_command is not None:
        self.supervisor.stop_child(self.stop_command).get()
      else:
        self.supervisor.kill_child(self.stop_signal).get()
      self.supervisor.actor_ref.stop()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
