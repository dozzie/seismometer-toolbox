#!/usr/bin/python
'''
UNIX domain socket writer.

.. autoclass:: UNIX
   :members:

'''
#-----------------------------------------------------------------------------

import os
import socket
from _connection_output import ConnectionOutput

#-----------------------------------------------------------------------------

class UNIX(ConnectionOutput):
  '''
  Sender passing message to another messenger through UNIX sockets.
  '''
  def __init__(self, path, spooler = None):
    '''
    :param path: socket path to send data to
    :param spooler: spooler object
    '''
    self.path = os.path.abspath(path)
    self.conn = None
    super(UNIX, self).__init__(spooler)

  def write(self, line):
    if self.conn is None:
      return False

    try:
      self.conn.send(line)
      return True
    except socket.error:
      # lost connection
      self.conn = None
      return False

  def is_connected(self):
    # FIXME: better check
    return (self.conn is not None)

  def repair_connection(self):
    try:
      conn = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
      conn.connect(self.path)
      self.conn = conn
      return True
    except socket.error:
      return False

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
