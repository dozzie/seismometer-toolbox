#!/usr/bin/python

import collections

#-----------------------------------------------------------------------------

#   * message spooler
#     * works on strings
#     * in-memory
#     * on-disk

#-----------------------------------------------------------------------------

class MemorySpooler:
  def __init__(self, max = None):
    self._queue = collections.deque()
    self._max = max
    self._size = 0

  def spool(self, line):
    self._size += len(line)
    self._queue.append(line)
    if self._max is not None:
      while self._size > self._max:
        self.drop_one()

  def peek(self):
    if self._size == 0:
      return None
    else:
      return self._queue[0]

  def drop_one(self):
    line = self._queue.popleft()
    self._size -= len(line)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
