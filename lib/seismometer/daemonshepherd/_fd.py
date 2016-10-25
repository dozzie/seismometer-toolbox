#!/usr/bin/python
'''
Close-on-exec flag
------------------

.. autofunction:: close_on_exec

'''
#-----------------------------------------------------------------------------

import fcntl

#-----------------------------------------------------------------------------

def close_on_exec(handle):
    '''
    :param handle: file handle or file descriptor to set close-on-exec flag on

    Set ``FD_CLOEXEC`` flag on a file handle or descriptor.
    '''
    if isinstance(handle, (int, long)):
        fd = handle
    else:
        fd = handle.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
