#!/usr/bin/python
'''
Running external program as daemon
----------------------------------

.. autofunction:: build

.. autoclass:: Daemon
   :members:

.. autoclass:: Command
   :members:

.. autoclass:: Signal
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
    :param spec: dictionary with daemon specification
    :return: :class:`Daemon`

    Build a :class:`Daemon` instance according to specification.

    **TODO**: Describe how this specification looks like (it comes from
    config file).
    '''

    # TODO: some small data validation, especially presence of required fields

    # TODO: STDOUT of admin commands should go to user
    command_defaults = {
        "environment":  spec.get("environment"),
        "cwd":          spec.get("cwd"),
        "user":         spec.get("user"),
        "group":        spec.get("group"),
        "stdout":       "/dev/null",
    }

    start_command = build_command({
        "command": spec.get("start_command"),
        "command_name": spec.get("argv0"),
        "stdout": spec.get("stdout"),
    }, command_defaults)

    admin_commands = {}
    for (name, cmdspec) in spec.get("commands", {}).items():
        admin_commands[name] = build_command(cmdspec, command_defaults)

    if "stop" not in admin_commands:
        if "stop_command" in spec:
            admin_commands["stop"] = build_command({
                "command": spec["stop_command"]
            }, command_defaults)
        else:
            admin_commands["stop"] = build_command({
                "signal": spec.get("stop_signal"),
            })

    return Daemon(
        start_command = start_command,
        admin_commands = admin_commands,
    )

def build_command(spec, defaults = {}):
    if not spec.get("command"):
        if spec.get("signal") is None:
            return Signal(signal.SIGTERM)
        else:
            return Signal(spec["signal"])

    def get_default(name):
        return spec.get(name, defaults.get(name))

    stdout_option = get_default("stdout")
    if stdout_option == "console" or stdout_option is None:
        stdout_option = None
    elif stdout_option == "/dev/null":
        stdout_option = Command.DEVNULL
    else: # assume it's `stdout_option == "log"'
        stdout_option = Command.PIPE

    return Command(
        command       = get_default("command"),
        command_name  = get_default("command_name"),
        environment   = get_default("environment"),
        cwd           = get_default("cwd"),
        stdout        = stdout_option,
        user          = get_default("user"),
        group         = get_default("group"),
    )

#-----------------------------------------------------------------------------

class _Constant:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<%s>" % (self.name,)

#-----------------------------------------------------------------------------

class Signal:
    '''
    Signal representation for administrative commands for :class:`Daemon`.

    Converting an instance to integer (``int(instance)``) results in signal
    number.
    '''
    def __init__(self, sig):
        '''
        :param sig: signal number or name

        Signal name ignores case and prepends "SIG" prefix if necessary, so
        any of the names are valid: ``"term"``, ``"sigterm"``, ``"TERM"``,
        ``"SIGTERM"``.
        '''
        if isinstance(sig, (str, unicode)):
            # convert sig from name to number
            sig = sig.upper()
            if not sig.startswith('SIG'):
                sig = 'SIG' + sig
            self.signal = signal.__dict__[sig]
        else: # integer
            self.signal = int(sig)

    def __int__(self):
        return self.signal

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if not isinstance(other, Signal):
            return False
        return self.signal == other.signal

    def send(self, pid = None, group = None):
        '''
        :return: ``True`` if signal was sent successfully, ``False`` on error

        Send a signal to process or process group.
        '''
        if pid is not None:
            try:
                os.kill(pid, self.signal)
                return True
            except OSError:
                return False
        if group is not None:
            try:
                os.killpg(group, self.signal)
                return True
            except OSError:
                return False

#-----------------------------------------------------------------------------

class Command:
    '''
    External command representation for doing :func:`fork()` + :func:`exec()`
    in a repeatable manner.

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
        if not isinstance(other, Command):
            return False
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

        # try spawning a child
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
    Single daemon representation and interaction channel. A daemon can be
    started or stopped.

    To set or read metadata (opaque to this class), use dictionary operations
    (get value, set value, ``del``, ``in`` to check key existence, ``len()``,
    iteration over keys).
    '''

    def __init__(self, start_command, admin_commands, metadata = None):
        '''
        :param start_command: command used to start the daemon
        :param admin_commands: dictionary with administrative commands
        :param metadata: dictionary with additional information about daemon
        '''

        self.metadata = metadata if metadata is not None else {}
        self.start_command = start_command
        self.admin_commands = admin_commands
        self.child_pid = None
        self.child_stdout = None

    def __del__(self):
        self.stop()

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        return self.start_command == other.start_command

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
        self.command("stop")
        self.reap()

    def has_command(self, cmd):
        '''
        :param cmd: name of the command

        Check if the daemon has particular administrative command.
        '''
        return cmd in self.admin_commands

    def command(self, cmd, env = None):
        '''
        :param cmd: name of the command to run

        Run an administrative command.
        '''
        if cmd not in self.admin_commands:
            raise KeyError("command %s not defined" % (cmd,))

        command = self.admin_commands[cmd]
        if isinstance(command, Signal):
            if self.child_pid is not None:
                # TODO: send to process group
                command.send(self.child_pid)
            return

        # NOTE: now command is an instance of `Command' class

        if self.child_pid is not None:
            environment = { "DAEMON_PID": str(self.child_pid) }
        else:
            environment = { "DAEMON_PID": "" }

        if env is not None:
            environment.update(env)

        # TODO: read and return STDOUT, if any
        # TODO: return exit code
        (pid, read_handle) = command.run(environment = environment)
        try:
            os.waitpid(pid, 0) # wait for termination of stop command
        except OSError:
            pass # errno ECHILD, child already reaped

    def replace_commands(self, source):
        '''
        :param source: source of admin commands
        :type source: :class:`Daemon`

        Replace admin commands of this instance with commands from
        :obj:`source`.
        '''
        self.admin_commands.clear()
        self.admin_commands.update(source.admin_commands)

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
