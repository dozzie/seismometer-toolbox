#!/usr/bin/python
'''
Available handle classes
------------------------

.. autoclass:: BaseHandle
   :members:

.. autoclass:: ShellStream
   :members:

.. autoexception:: HandleEOF
   :members:

'''
#-----------------------------------------------------------------------------

import time
import re
import json
import signal
import logging
import subprocess
import seismometer.message
import fcntl
import os
import errno

__all__ = [
    'BaseHandle', 'ShellStream',
    'HandleEOF',
]

#-----------------------------------------------------------------------------

class HandleEOF(Exception):
    '''
    Exception to signal that :class:`BaseHandle` instance encountered EOF when
    reading from its descriptor, thus it needs maintenance (close and open).
    '''
    pass

#-----------------------------------------------------------------------------

class BaseHandle(object):
    '''
    Base class for handle-based checks.

    Instance should start in a closed state, i.e. should not start any
    subprocesses nor setup sockets. This work should be left for
    :meth:`open()` method.

    This class contains no special initialization (i.e. default
    :meth:`__init__()`).
    '''

    def fileno(self):
        '''
        :return: integer or ``None``

        Return a file descriptor the handle reads from for
        :class:`seismometer.poll.Poll`.
        '''
        raise NotImplementedError("method fileno() not implemented")

    def open(self):
        '''
        Open the handle. This is the method that should start subprocesses and
        setup necessary sockets.

        On any error, the method should raise an exception.
        '''
        raise NotImplementedError("method open() not implemented")

    def close(self):
        '''
        Close the handle. This method will be called after
        :meth:`read_messages()` reports an EOF.
        '''
        raise NotImplementedError("method close() not implemented")

    def read_messages(self):
        '''
        :return: list of messages (dict or
            :class:`seismometer.message.Message`)
        :throws: :exc:`HandleEOF`, :exc:`Exception`

        Read and parse messages received on this handle. If no messages are
        available for read, the method should return empty list.

        If an end-of-file is encountered, :exc:`HandleEOF` should be raised,
        after which :meth:`close()` will be called by the parent. Any other
        exception signals that the error was just a processing one, and
        :meth:`close()` method will not be called.

        Note that this method should not block. To set a descriptor to
        a non-blocking state, see :meth:`BaseHandle.set_nonblocking()`.
        '''
        # return a list of messages (empty if nothing to read)
        # raise HandleEOF on EOF
        # raise an exception on data processing error
        raise NotImplementedError("method readlines() not implemented")

    @staticmethod
    def set_close_on_exec(handle):
        '''
        :param handle: handle (object with :meth:`fileno()` method) or file
            descriptor (integer)

        Set close-on-exec flag, so the file descriptor doesn't leak to
        subprocesses.
        '''
        fd = handle.fileno() if hasattr(handle, 'fileno') else handle
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

    @staticmethod
    def set_nonblocking(handle):
        '''
        :param handle: handle (object with :meth:`fileno()` method) or file
            descriptor (integer)

        Set non-blocking flag, so the reads return immediately if no data is
        available.

        Note that reading from a handle in non-blocking mode results in an
        :exc:`IOError` exception with errno set to :obj:`errno.EAGAIN` or
        :obj:`errno.EWOULDBLOCK` (under Linux these two errnos are equal).
        '''
        fd = handle.fileno() if hasattr(handle, 'fileno') else handle
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

#-----------------------------------------------------------------------------

class ShellStream(BaseHandle):
    '''
    Handle for reading a stream of lines from an external tool (e.g.
    :manpage:`vmstat(8)` or :manpage:`iostat(1)`) and parsing them to messages
    for further processing.
    '''
    def __init__(self, command, parse = None):
        '''
        :param command: command to run (string for shell command, or list of
            strings for direct command to run)
        :param parse: function to parse a line read from the command

        If :obj:`parse` argument is ``None``, :func:`json.loads()` is used,
        meaning that the command prints JSON objects, one per line.

        Parse function should return a dict,
        :class:`seismometer.message.Message`, or list or tuple of these. If
        the function needs to ignore the line, it should return an empty list
        or tuple rather than ``None``.
        '''
        super(ShellStream, self).__init__()
        self.command = command
        self.parse = parse if parse is not None else json.loads
        self.child = None

    def __del__(self):
        self.close()

    def open(self):
        self.close() # make sure we don't lose any subprocess
        use_shell = not isinstance(self.command, (list, tuple))
        # TODO: raise an exception if spawning a child fails
        self.child = subprocess.Popen(
            self.command,
            stdin = open("/dev/null"),
            stdout = subprocess.PIPE,
            shell = use_shell,
        )
        # close-on-exec is necessary for the descriptor not to leak to another
        # subprocesses
        BaseHandle.set_close_on_exec(self.child.stdout)
        BaseHandle.set_nonblocking(self.child.stdout)

    def close(self):
        if self.child is not None:
            try:
                # a child should not close its STDOUT
                self.child.kill()
            except OSError:
                pass # child reaped already
            self.child.stdout.close()
            self.child.wait()
            self.child = None

    def fileno(self):
        if self.child is not None:
            return self.child.stdout.fileno()
        return None

    def read_messages(self):
        result = []
        for line in self._readlines():
            rec = self.parse(line)
            if rec is None:
                pass
            elif isinstance(rec, (list, tuple)):
                result.extend(rec)
            else:
                result.append(rec)
        return result

    def _readlines(self):
        '''
        :return: list of strings
        :throws: :exc:`HandleEOF`, :exc:`Exception`

        Read all available lines from the child.
        '''
        if self.child is None:
            raise HandleEOF("child process not running")

        lines = []
        try:
            line = self.child.stdout.readline()
            while line != '':
                lines.append(line)
                line = self.child.stdout.readline()

            # EOF, return whatever was read up until now or report error
            # properly
            if len(lines) > 0:
                return lines

            exit_code = self.child.poll()
            if exit_code is None:
                raise HandleEOF("child process closed its STDOUT")
            elif exit_code == 0:
                raise HandleEOF("child process terminated")
            elif exit_code > 0:
                raise HandleEOF(
                    "child process terminated; exit code %d" % (exit_code,)
                )
            else: # exit_code < 0, died on signal
                raise HandleEOF(
                    "child process died; signal %d" % (-exit_code,)
                )
        except IOError, e:
            if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                # no more data to read; that's OK
                return lines
            raise

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
