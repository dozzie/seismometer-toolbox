#!/usr/bin/python

import os
import sys
import signal
import time
import re

#-----------------------------------------------------------------------------

class Command:
  DEVNULL = object()
  PIPE = object()

  SHELL_META = re.compile('[]\'"$&*()`{}\\\\;<>?[]')
  SPACE = re.compile('[ \t\r\n]+')

  def __init__(self, command, environment = None, cwd = None, stdout = None):
    self.environment = environment
    self.cwd = cwd
    self.stdout = stdout
    if Command.SHELL_META.search(command):
      self.args = ["/bin/sh", "-c", command]
      self.command = "/bin/sh"
    else:
      self.args = Command.SPACE.split(command)
      self.command = self.args[0]

  def run(self):
    if self.stdout is Command.PIPE:
      (read_end, write_end) = os.pipe()
    elif self.stdout is Command.DEVNULL:
      read_end = None
      write_end = os.open('/dev/null', os.O_WRONLY)
    else:
      read_end  = None
      write_end = None

    # try spawn child
    pid = os.fork()
    if pid != 0:
      # in parent: close writing end of pipe (if any), make reading end a file
      # handle (if any), return PID + read file handle
      if read_end is None:
        return (pid, None)
      else:
        read_end = os.fdopen(read_end, 'r')
        os.close(write_end)
        return (pid, read_end)

    # XXX: child process

    # set the child a group leader (^C in shell should not kill the process,
    # it's a parent's job)
    os.setpgrp()

    # close reading end of pipe, if any
    if read_end is not None:
      os.close(read_end)

    # redirect STDIN
    devnull = open('/dev/null')
    os.dup2(devnull.fileno(), 0)
    devnull.close()

    # redirect STDOUT and STDERR to pipe, if any
    if write_end is not None:
      os.dup2(write_end, 1)
      os.dup2(write_end, 2)
      os.close(write_end)

    # change working directory if requested
    if self.cwd is not None:
      os.chdir(self.cwd)

    # set environment if requested
    if self.environment is not None:
      for e in self.environment:
        os.environ[e] = self.environment[e]

    # execute command and exit with error if failed
    os.execvp(self.command, self.args)
    os._exit(127)

#-----------------------------------------------------------------------------

class Daemon:
  def __init__(self, start_command, stop_command = None, stop_signal = None,
               environment = None, cwd = None, stdout = None):
    if stdout is None or stdout == 'stdout':
      self.start_command = Command(start_command, environment, cwd)
    elif stdout == '/dev/null':
      self.start_command = Command(
        start_command, environment, cwd, Command.DEVNULL
      )
    elif stdout == 'pipe':
      self.start_command = Command(
        start_command, environment, cwd, Command.PIPE
      )

    if stop_command is not None:
      self.stop_command = Command(
        stop_command, environment, cwd, Command.DEVNULL
      )
      self.stop_signal = None
    else:
      self.stop_command = None
      if stop_signal is None:
        self.stop_signal = signal.SIGTERM
      elif isinstance(stop_signal, (str, unicode)):
        # convert stop_signal from name to number
        if stop_signal.startswith('SIG'):
          self.stop_signal = signal.__dict__[stop_signal]
        else:
          self.stop_signal = signal.__dict__['SIG' + stop_signal]
      else:
        self.stop_signal = stop_signal

    self.child_pid = None
    self.child_stdout = None

  def __del__(self):
    self.stop()

  #-------------------------------------------------------------------
  # starting and stopping daemon

  def start(self):
    if self.child_pid is not None:
      # TODO: raise an error (child is already running)
      return
    (self.child_pid, self.child_stdout) = self.start_command.run()

  def stop(self):
    if self.child_pid is None:
      # NOTE: don't raise an error (could be called from __del__() when the
      # child is not running)
      return

    # TODO: make this command asynchronous
    if self.stop_command is not None:
      (pid, ignore) = self.stop_command.run()
      os.waitpid(pid, 0) # wait for termination of stop command
    else:
      os.killpg(self.child_pid, self.stop_signal)
    self.reap()

  #-------------------------------------------------------------------
  # filehandle methods

  def fileno(self):
    if self.child_stdout is not None:
      return self.child_stdout.fileno()
    else:
      return None

  def readline(self):
    if self.child_stdout is not None:
      return self.child_stdout.readline()
    else:
      return None

  def close(self):
    if self.child_stdout is not None:
      self.child_stdout.close()
      self.child_stdout = None

  #-------------------------------------------------------------------
  # child process management

  def is_alive(self):
    if self.child_pid is None:
      # no child was started
      return False
    if os.waitpid(self.child_pid, os.WNOHANG) != (0,0):
      # child was started, but has just exited
      self.child_pid = None
      return False

    # child is still running
    return True

  def reap(self):
    if self.child_pid is None:
      self.close() # in case it was still opened
      return

    self.close() # TODO: read self.child_stdout (and discard?)
    os.waitpid(self.child_pid, 0)
    self.child_pid = None

  #-------------------------------------------------------------------

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
