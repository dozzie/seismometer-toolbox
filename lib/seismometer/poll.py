#!/usr/bin/python
'''
Input descriptors polling
-------------------------

.. autoclass:: Poll
   :members:

'''
#-----------------------------------------------------------------------------

import select
import errno

#-----------------------------------------------------------------------------

class Poll:
    '''
    Poll filehandles for input.

    This is convenience wrapper around :mod:`select` module to work with
    filehandles instead of file descriptors.
    '''

    def __init__(self):
        self._poll = select.poll()
        self._known_fds = {}
        self._object_fds = {}

    def add(self, handle):
        '''
        :param handle: file handle (e.g. :obj:`file` object, but anything with
            :meth:`fileno` method)

        Add a handle to poll list. If ``handle.fileno()`` returns ``None``,
        the handle is not added. The same stands for objects that already were
        added (check is based on file descriptor).
        '''
        fd = handle.fileno()
        if fd is None or fd in self._known_fds:
            return

        # remember for later
        self._known_fds[fd] = handle
        self._object_fds[id(handle)] = fd
        self._poll.register(fd, select.POLLIN | select.POLLERR)

    def remove(self, handle):
        '''
        :param handle: file handle, the same as for :meth:`add`

        Remove file handle from poll list. Handle must still be the same
        object as passed to :meth:`add()` method, but may be closed.
        '''
        if id(handle) not in self._object_fds:
            return
        fd = self._object_fds[id(handle)]

        del self._known_fds[fd]
        del self._object_fds[id(handle)]
        self._poll.unregister(fd)

    def poll(self, timeout = 100):
        '''
        :param timeout: timeout in milliseconds for *poll* operation
        :return: list of file handles added with :meth:`add` method

        Check whether any data arrives on descriptors. File handles
        (*handles*, not *descriptors*) that are ready for reading are returned
        as a list.

        Method works around calls interrupted by signals (terminates early
        instead of throwing an exception).
        '''
        try:
            result = self._poll.poll(timeout)
            return [
                self._known_fds[r[0]]
                for r in result
                if r[0] in self._known_fds
            ]
        except select.error, e:
            if e.args[0] == errno.EINTR: # in case some signal arrives
                return []
            else: # other error, rethrow
                raise

    def count(self):
        '''
        Count the descriptors added to the poll.
        '''
        return len(self._known_fds)

    def empty(self):
        '''
        Check if the poll is empty (no descriptors).
        '''
        return (len(self._known_fds) == 0)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
