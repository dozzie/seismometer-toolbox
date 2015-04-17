#!/usr/bin/python
'''
Running external program as daemon
----------------------------------

.. autoclass:: Daemon
   :members:

.. autoclass:: Command
   :members:

'''
#-----------------------------------------------------------------------------

import os
import sys
import signal
import time
import re

#-----------------------------------------------------------------------------

class Command:
    '''
    Class for doing :func:`fork` + :func:`exec` in repeatable manner.

    Class has defined operators ``==`` and ``!=``, so objects are compared
    according to command line and its run environment (variables, *CWD*,
    *STDOUT*).
    '''

    DEVNULL = object()
    '''
    Constant for directing command's output to :file:`/dev/null`.
    '''

    PIPE = object()
    '''
    Constant for directing command's output through a pipe.
    '''

    SHELL_META = re.compile('[]\'"$&*()`{}\\\\;<>?[]')
    SPACE = re.compile('[ \t\r\n]+')

    def __init__(self, command, environment = None, cwd = None, stdout = None):
        '''
        :param command: command to be run (could be a shell snippet)
        :param environment: environment variables to be added/replaced in
          current environment
        :type environment: dict with string:string mapping
        :param cwd: directory to run command in
        :param stdout: where to direct output from the command

        Command's output could be sent as it is for parent process
        (:obj:`stdout` set to ``None``), silenced out (:const:`DEVNULL`) or
        intercepted (:const:`PIPE`).
        '''
        self.environment = environment
        self.cwd = cwd
        self.stdout = stdout
        if Command.SHELL_META.search(command):
            self.args = ["/bin/sh", "-c", command]
            self.command = "/bin/sh"
        else:
            self.args = Command.SPACE.split(command)
            self.command = self.args[0]

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        return self.environment == other.environment and \
               self.cwd         == other.cwd         and \
               self.stdout      == other.stdout      and \
               self.args        == other.args        and \
               self.command     == other.command

    def run(self):
        '''
        :return: ``(pid, read_end)`` or ``(pid, None)``

        Run the command within its environment. Child process starts its own
        process group, so if it's a shell command, it's easier to kill whole
        set of processes. *STDIN* of the child process is always redirected to
        :file:`/dev/null`.

        If :obj:`stdout` parameter to constructor was :const:`PIPE`, read end
        of the pipe (``file`` object) is returned in the tuple.
        '''
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
            # in parent: close writing end of pipe (if any), make reading end
            # a file handle (if any), return PID + read file handle
            if read_end is None:
                return (pid, None)
            else:
                read_end = os.fdopen(read_end, 'r')
                os.close(write_end)
                return (pid, read_end)

        # XXX: child process

        # set the child a group leader (^C in shell should not kill the
        # process, it's a parent's job)
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
    '''
    Class representing single daemon, which can be started or stopped.
    '''

    def __init__(self, start_command, stop_command = None, stop_signal = None,
                 environment = None, cwd = None, stdout = None):
        '''
        :param start_command: command used to start the daemon
        :param stop_command: command used to stop the daemon instead of signal
        :param stop_signal: signal used to stop the daemon
        :param environment: environment variables to be added/replaced when
          running commands (start and stop)
        :type environment: dict with string:string mapping
        :param cwd: directory to run commands in (both start and stop)
        :param stdout: where to direct output from the command
        :type stdout: ``"stdout"`` (or ``None``), ``"/dev/null"`` or
          ``"pipe"``

        For stopping the daemon, command has the precedence over signal.
        If both :obj:`stop_command` and :obj:`stop_signal` are ``None``,
        ``SIGTERM`` is used.
        '''

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
                stop_signal = stop_signal.upper()
                if not stop_signal.startswith('SIG'):
                    stop_signal = 'SIG' + stop_signal
                self.stop_signal = signal.__dict__[stop_signal]
            else:
                self.stop_signal = stop_signal

        self.child_pid = None
        self.child_stdout = None

    def __del__(self):
        self.stop()

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        return self.start_command == other.start_command and \
               self.stop_command  == other.stop_command  and \
               self.stop_signal   == other.stop_signal

    #-------------------------------------------------------------------
    # starting and stopping daemon

    def start(self):
        '''
        Start the daemon.
        '''
        if self.child_pid is not None:
            # TODO: raise an error (child is already running)
            return
        (self.child_pid, self.child_stdout) = self.start_command.run()

    def stop(self):
        '''
        Stop the daemon.
        '''
        if self.child_pid is None:
            # NOTE: don't raise an error (could be called from __del__() when
            # the child is not running)
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
        '''
        Return file descriptor for the daemon's pipe (``None`` if daemon's
        output is not intercepted).

        Method intended for :func:`select.poll`.
        '''
        if self.child_stdout is not None:
            return self.child_stdout.fileno()
        else:
            return None

    def readline(self):
        '''
        Read a single line from daemon's output (``None`` if daemon's output
        is not intercepted).
        '''
        if self.child_stdout is not None:
            return self.child_stdout.readline()
        else:
            return None

    def close(self):
        '''
        Close read end (this process' end) of daemon's output.
        '''
        if self.child_stdout is not None:
            self.child_stdout.close()
            self.child_stdout = None

    #-------------------------------------------------------------------
    # child process management

    def pid(self):
        '''
        Return PID of the daemon (``None`` if daemon is stopped).
        '''
        return self.child_pid

    def is_alive(self):
        '''
        Check if the daemon is still alive.
        '''
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
        '''
        Close our end of daemon's *STDOUT* and wait for daemon's termination.
        '''
        if self.child_pid is None:
            self.close() # in case it was still opened
            return

        self.close() # TODO: read self.child_stdout (and discard?)
        os.waitpid(self.child_pid, 0)
        self.child_pid = None

    #-------------------------------------------------------------------

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
