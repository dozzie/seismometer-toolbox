#!/usr/bin/python

import os
import subprocess
import pykka
import time
import re

#-----------------------------------------------------------------------------

class DaemonSupervisor(pykka.ThreadingActor):
  SHELL_META = re.compile('[]\'"$&*()`{}\\\\;<>?[]')
  SPACE = re.compile('[ \t\r\n]+')

  def __init__(self, command, environment, cwd, stdout, backoff):
    super(DaemonSupervisor, self).__init__()
    if DaemonSupervisor.SHELL_META.search(command):
      self.command = command
    else:
      self.command = DaemonSupervisor.SPACE.split(command)
    self.environment = environment
    self.cwd = cwd
    self.stdout = stdout
    if backoff is None:
      self.backoff = [1, 15, 15, 60, 300]
    else:
      self.backoff = backoff
    self.backoff_position = 0
    self.backoff_time = time.time()
    self.child = None
    self.stop = False

  def start_child(self):
    self.stop = False
    # TODO: read STDOUT/STDERR and convert it to log or a message
    if isinstance(self.command, list):
      self.child = subprocess.Popen(
        self.command,
        stdin  = open("/dev/null"),
        stdout = open("/dev/null", "w"),
        stderr = subprocess.STDOUT,
      )
    else:
      self.child = subprocess.Popen(
        self.command, shell = True,
        stdin  = open("/dev/null"),
        stdout = open("/dev/null", "w"),
        stderr = subprocess.STDOUT,
      )

    # XXX: enter child monitoring loop
    self.actor_ref.ask({"monitor": True}, block = False)

  def stop_child(self, command):
    self.stop = True
    if self.child is None:
      return

    os.system(command)
    while self.child.poll() is None:
      # TODO: don't wait for infinity
      time.sleep(0.1)
    self.child = None

  def kill_child(self, signal):
    self.stop = True
    if self.child is None:
      return

    # TODO: send signal to child
    os.kill(self.child.pid, signal)
    while self.child.poll() is None:
      # TODO: don't wait for infinity
      time.sleep(0.1)
    self.child = None

  def sleep_backoff(self):
    backoff = self.backoff[self.backoff_position]
    # reset backoff if last backoff sleep was long ago (minimum 10s)
    if backoff > 10 and time.time() - self.backoff_time > 2 * backoff:
      self.backoff_position = 0
      backoff = self.backoff[self.backoff_position]

    time.sleep(backoff)
    if self.backoff_position < len(self.backoff):
      self.backoff_position += 1

  def child_ok(self):
    return self.child is not None and self.child.poll() is None

  def on_receive(self, message):
    if self.stop:
      return

    if self.child_ok():
      # TODO: read something from child's STDOUT (timeout 100ms)
      time.sleep(1) # TODO: time.sleep(0.1)
    else:
      self.sleep_backoff()
      self.start_child()

    # loop (somewhat indirect)
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
