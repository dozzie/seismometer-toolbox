#!/usr/bin/python
'''
STDIN input reader.

.. autoclass:: STDIN
   :members:

'''
#-----------------------------------------------------------------------------

import sys

#-----------------------------------------------------------------------------

class STDIN:
  '''
  Socket-like class for reading from standard input.
  '''
  def __init__(self):
    pass # nothing to do here

  def readline(self):
    line = sys.stdin.readline()
    if line == '':
      return (None, None)
    else:
      return (None, line.strip())

  def fileno(self):
    return sys.stdin.fileno()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
