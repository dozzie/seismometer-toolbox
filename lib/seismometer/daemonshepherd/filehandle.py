#!/usr/bin/python
'''
Close-on-exec flag
------------------

.. autofunction:: set_close_on_exec()

.. autofunction:: set_nonblocking()

'''
#-----------------------------------------------------------------------------

import fcntl
import os

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
