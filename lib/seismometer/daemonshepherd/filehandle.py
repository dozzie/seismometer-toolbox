#!/usr/bin/python
'''
File handle routines and constants
----------------------------------

.. autofunction:: set_close_on_exec()

.. autofunction:: set_nonblocking()

.. autodata:: EOF

'''
#-----------------------------------------------------------------------------

import fcntl
import os

#-----------------------------------------------------------------------------

class _Constant:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<%s>" % (self.name,)

EOF = _Constant("EOF")
'''
Marker to be returned by ``read()`` methods when the connection or pipe is
closed.
'''

#-----------------------------------------------------------------------------

def set_close_on_exec(handle):
    '''
    :param handle: file handle or file descriptor to set close-on-exec flag on

    Set ``FD_CLOEXEC`` flag on a file handle or descriptor.
    '''
    fd = handle.fileno() if hasattr(handle, 'fileno') else handle
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

def set_nonblocking(handle):
    '''
    :param handle: file handle or file descriptor

    Set file handle to non-blocking mode.
    '''
    fd = handle.fileno() if hasattr(handle, 'fileno') else handle
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
