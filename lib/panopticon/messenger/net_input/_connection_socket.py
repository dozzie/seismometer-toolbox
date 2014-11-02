#!/usr/bin/python
'''
Base class for connection-oriented input sockets. Such sockets don't return
data to be read. Instead, they return another connection objects and one reads
incoming data from those.

.. autoclass:: ConnectionSocket
   :members:

'''
#-----------------------------------------------------------------------------

class ConnectionSocket:
  '''
  Connection-oriented generic socket.
  '''
  def accept(self):
    '''
    Return a connection suitable for ``poll()``.
    '''
    raise NotImplementedError()

  def fileno(self):
    '''
    Return a file descriptor.
    '''
    raise NotImplementedError()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
