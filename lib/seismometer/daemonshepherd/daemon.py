#!/usr/bin/python
'''
Running external program as daemon
----------------------------------

.. autofunction:: build()

.. autoclass:: Daemon
   :members:

.. autoclass:: Command
   :members:

'''
#-----------------------------------------------------------------------------

import os
import sys
import errno
import signal
import time
import re
import setguid
import filehandle

#-----------------------------------------------------------------------------

def build(spec):
    '''
    :spec: dictionary with daemon specification
    :return: :class:`Daemon`

    Build a :class:`Daemon` instance according to specification.

    **TODO**: Describe how this specification looks like (it comes from
    config file).
    '''

    stdout_option = spec.get("stdout")
    if stdout_option == "console":
        stdout_option = None
    elif stdout_option == "/dev/null":
        pass
    else: # assume it's `stdout_option == "log"'
        stdout_option = "pipe"

    # TODO: some small data validation, especially presence of required fields

    return Daemon(
        start_command = spec.get("start_command"),
        command_name  = spec.get("argv0"),
        stop_command  = spec.get("stop_command"),
        stop_signal   = spec.get("stop_signal"),
        environment   = spec.get("environment"),
        cwd           = spec.get("cwd"),
        stdout        = stdout_option,
        user          = spec.get("user"),
        group         = spec.get("group"),
    )

#-----------------------------------------------------------------------------

class _Constant:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<%s>" % (self.name,)

#-----------------------------------------------------------------------------

class Command:
    '''
    Class for doing :func:`fork()` + :func:`exec()` in repeatable manner.

    Class has defined operators ``==`` and ``!=``, so objects are compared
    according to command line and its run environment (variables, *CWD*,
    *STDOUT*).
    '''

    DEVNULL = _Constant("Command.DEVNULL")
    '''
    Constant for directing command's output to :file:`/dev/null`.
    '''

    PIPE = _Constant("Command.PIPE")
    '''
    Constant for directing command's output through a pipe.
    '''

    SHELL_META = re.compile('[]\'"$&*()`{}\\\\;<|>?[]')
    SPACE = re.compile('[ \t\r\n]+')

    def __init__(self, command, command_name = None,
                 environment = None, cwd = None, stdout = None,
                 user = None, group = None):
        '''
        :param command: command to be run (could be a shell snippet)
        :param environment: environment variables to be added/replaced in
            current environment
        :type environment: dict with string:string mapping
        :param command_name: command name (``argv[0]``) to be passed to
            :func:`exec()`
        :param cwd: directory to run command in
        :param stdout: where to direct output from the command
        :param user: user to run as
        :param group: group to run as (defaults to primary group of
            :obj:`user`)

        Command's output could be sent as it is for parent process
        (:obj:`stdout` set to ``None``), silenced out (:const:`DEVNULL`) or
        intercepted (:const:`PIPE`).
        '''
        self.environment = environment
        self.cwd = cwd
        self.user = user
        self.group = group
        self.stdout = stdout
        if Command.SHELL_META.search(command):
            self.args = ["/bin/sh", "-c", command]
            self.command = "/bin/sh"
        else:
            self.args = Command.SPACE.split(command)
            self.command = self.args[0]
        if command_name is not None:
            self.args[0] = command_name

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        return self.environment == other.environment and \
               self.cwd         == other.cwd         and \
               self.stdout      == other.stdout      and \
               self.args        == other.args        and \
               self.command     == other.command     and \
               self.user        == other.user        and \
               self.group       == other.group

    def run(self, environment = None):
        '''
        :type environment: dict with string:string mapping, an addition to
            :obj:`self.environment`
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
            if write_end is not None:
                os.close(write_end)
            if read_end is not None:
                read_end = os.fdopen(read_end, 'r')
            return (pid, read_end)

        # XXX: child process

        # set the child a group leader (^C in shell should not kill the
        # process, it's a parent's job)
        os.setpgrp()

        # set UID/GID as necessary
        setguid.setguid(self.user, self.group)

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
        if environment is not None:
            for e in environment:
                os.environ[e] = environment[e]

        # execute command and exit with error if failed
        os.execvp(self.command, self.args)
        os._exit(127)

#-----------------------------------------------------------------------------

class Daemon:
    '''
    Class representing single daemon, which can be started or stopped.

    To set or read metadata (opaque to this class), use dictionary operations
    (get value, set value, ``del``, ``in`` to check key existence, ``len()``,
    iteration over keys).
    '''

    def __init__(self, start_command, stop_command = None, stop_signal = None,
                 command_name = None, metadata = None,
                 environment = None, cwd = None, stdout = None,
                 user = None, group = None):
        '''
        :param start_command: command used to start the daemon
        :param stop_command: command used to stop the daemon instead of signal
        :param stop_signal: signal used to stop the daemon
        :param command_name: command name (``argv[0]``) to be passed to
            :func:`exec()`
        :param metadata: additional information about daemon
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

        self.metadata = metadata if metadata is not None else {}

        if stdout is None or stdout == 'stdout':
            stdout = None
        elif stdout == '/dev/null':
            stdout = Command.DEVNULL
        elif stdout == 'pipe':
            stdout = Command.PIPE

        self.start_command = Command(
            command = start_command,
            command_name = command_name,
            environment = environment,
            cwd = cwd,
            stdout = stdout,
            user = user,
            group = group,
        )

        if stop_command is not None:
            self.stop_command = Command(
                command = stop_command,
                environment = environment,
                cwd = cwd,
                stdout = Command.DEVNULL,
                user = user,
                group = group,
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
    # daemon metadata

    def __getitem__(self, name):
        if name not in self.metadata:
            raise KeyError('no such key: %s' % (name,))
        return self.metadata[name]

    def __setitem__(self, name, value):
        self.metadata[name] = value

    def __delitem__(self, name):
        if name in self.metadata:
            del self.metadata[name]

    def __contains__(self, name):
        return (name in self.metadata)

    def __len__(self):
        return len(self.metadata)

    def __iter__(self):
        return self.metadata.__iter__()

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
        if self.child_stdout is not None:
            filehandle.set_close_on_exec(self.child_stdout)
            filehandle.set_nonblocking(self.child_stdout)

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
            stop_env = {
                "DAEMON_PID": str(self.child_pid),
            }
            (pid, ignore) = self.stop_command.run(environment = stop_env)
            try:
                os.waitpid(pid, 0) # wait for termination of stop command
            except OSError:
                pass # errno ECHILD, child already reaped
        else:
            try:
                os.killpg(self.child_pid, self.stop_signal)
            except OSError:
                pass # errno ESRCH, child has died already
        self.reap()

    #-------------------------------------------------------------------
    # filehandle methods

    def fileno(self):
        '''
        Return file descriptor for the daemon's pipe (``None`` if daemon's
        output is not intercepted).

        Method intended for :func:`select.poll()`.
        '''
        if self.child_stdout is not None:
            return self.child_stdout.fileno()
        else:
            return None

    def readline(self):
        '''
        Read a single line from daemon's output. If nothing is ready to be
        read, also when daemon's output is not intercepted, ``None`` is
        returned (the call is non-blocking).

        Method returns :obj:`seismometer.daemonshepherd.filehandle.EOF` when
        the child or terminated or otherwise closed its *STDOUT*.
        '''
        if self.child_stdout is None:
            return None

        try:
            line = self.child_stdout.readline()
        except IOError, e:
            if e.errno == errno.EWOULDBLOCK or e.errno == errno.EAGAIN:
                # nothing more to read at the moment
                return None
            else:
                raise

        if line == "":
            return filehandle.EOF
        else:
            return line

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
            # no child was started or child was already reaped
            return False
        try:
            if os.waitpid(self.child_pid, os.WNOHANG) != (0,0):
                # child was started, but has just exited
                self.child_pid = None
                return False
        except OSError:
            # ECHILD errno, no more children (somebody reaped the child before
            # this check)
            self.child_pid = None
            return False

        # child is still running
        return True

    def reap(self):
        '''
        Close our end of daemon's *STDOUT* and wait for daemon's termination.
        '''
        # in case it was still opened
        self.close() # TODO: read self.child_stdout (and discard? return?)

        if self.child_pid is None:
            return

        try:
            os.waitpid(self.child_pid, 0)
        except OSError:
            pass # errno ECHILD, child already reaped
        self.child_pid = None

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
