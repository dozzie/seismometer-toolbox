#!/usr/bin/python
'''
Fork as a daemon process
------------------------

.. autofunction:: detach

.. autofunction:: detach_succeeded

.. autofunction:: child_process

.. autofunction:: parent_process

'''
#-----------------------------------------------------------------------------

import os
import sys

#-----------------------------------------------------------------------------

def detach(new_cwd = None):
    '''
    :param new_cwd: directory to :func:`chdir()` to (``None`` if no change
        needed)

    Detach current program from terminal (:func:`fork()` + :func:`exit()`).

    Detached (child) process will have *STDIN*, *STDOUT* and *STDERR*
    redirected to :file:`/dev/null`.
    '''
    if os.fork() == 0:
        if new_cwd is not None:
            os.chdir(new_cwd)
        child_process()
    else:
        parent_process()

def child_process():
    '''
    Operations to initialize child process after detaching.

    This consists mainly of redirecting *STDIN*, *STDOUT* and *STDERR* to
    :file:`/dev/null`.

    **NOTE**: This is not the place to acknowledge success. There are other
    operations, like creating listening sockets. See
    :func:`detach_succeeded()`.
    '''
    # replace STDIN, STDOUT and STDERR
    new_stdin_fd = os.open('/dev/null', os.O_RDONLY)
    new_stdout_fd = os.open('/dev/null', os.O_WRONLY)
    os.dup2(new_stdin_fd, 0)
    os.dup2(new_stdout_fd, 1)
    os.dup2(new_stdout_fd, 2)
    os.close(new_stdin_fd)
    os.close(new_stdout_fd)
    # detach from controlling terminal
    os.setsid()

def parent_process():
    '''
    Operations to do in parent process, including terminating the parent.
    '''
    # TODO: wait for child to acknowledge success
    sys.exit(0)

def detach_succeeded():
    '''
    Acknowledge success of detaching child to the parent.
    '''
    # TODO: implement me
    pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
