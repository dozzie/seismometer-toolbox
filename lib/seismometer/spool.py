#!/usr/bin/python
'''
Spoolers for data that needs to be sent in case of network connectivity
problems.

.. autoclass:: MemorySpooler
   :members:

'''
#-----------------------------------------------------------------------------

import collections

#-----------------------------------------------------------------------------

# TODO: class DiskSpooler

#-----------------------------------------------------------------------------

class MemorySpooler:
    '''
    Spooler that keeps data in memory.
    '''
    def __init__(self, max = 20 * 1024 * 1024):
        '''
        :param max: maximum number of bytes to keep in queue (defaults to 20M)
        '''
        self._queue = collections.deque()
        self._max = max
        self._size = 0

    def spool(self, line):
        '''
        :param line: line to spool
        :returns: number of messages dropped to keep the queue under its limit

        Spool single line. If spool limit was set, oldest entries will be
        dropped.
        '''
        self._size += len(line)
        self._queue.append(line)
        dropped_count = 0
        if self._max is not None:
            while self._size > self._max:
                self.drop_one()
                dropped_count += 1
        return dropped_count

    def peek(self):
        '''
        Retrieve the oldest line from spool. The line *will not* be removed from
        spool.
        '''
        if self._size == 0:
            return None
        else:
            return self._queue[0]

    def drop_one(self):
        '''
        Drop the oldest line from spool.
        '''
        line = self._queue.popleft()
        self._size -= len(line)

    def __len__(self):
        '''
        Return number of messages in the queue.
        '''
        return len(self._queue)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
