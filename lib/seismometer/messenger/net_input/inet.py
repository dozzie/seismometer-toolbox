#!/usr/bin/python
'''
Network sockets: TCP and UDP.

.. autoclass:: TCP
   :members:

.. autoclass:: TCPConnection
   :members:

.. autoclass:: UDP
   :members:

'''
#-----------------------------------------------------------------------------

import sys
import os
import socket
import seismometer.poll
import seismometer.message
import Queue
import json

from _connection_socket import ConnectionSocket

#-----------------------------------------------------------------------------

class TCP(ConnectionSocket):
  '''
  Listening TCP socket. Not intended for reading itself, instead returns
  connection objects.
  '''
  def __init__(self, host, port):
    '''
    :param host: bind address
    :type host: string or ``None``
    :param port: bind address
    :type port: integer
    '''
    self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if host is not None:
      self.conn.bind((host, port))
    else:
      self.conn.bind(('', port))
    self.conn.listen(256)

  def accept(self):
    '''
    :rtype: TCPConnection

    Accept a connection.
    '''
    (client, (host, port)) = self.conn.accept()
    client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    return TCPConnection(client, host)

  def fileno(self):
    return self.conn.fileno()

class TCPConnection:
  '''
  TCP connection reader.
  '''
  def __init__(self, conn, host):
    '''
    :param conn: connection descriptor
    :type conn: socket.socket()
    :param host: remote end address
    :type host: string
    '''
    self.conn = conn
    # TODO: resolve hostname (some cache maybe?)
    self.host = host

  def __del__(self):
    self.close()

  def close(self):
    '''
    Close TCP connection.
    '''
    if self.conn is not None:
      self.conn.close()
      self.conn = None

  def readline(self):
    '''
    :return: ``(host, string)``

    Read a single line from connection.
    '''
    line = self.conn.recv(16384)
    if line == '':
      return (None, None)
    else:
      # XXX: assume the line is always transmitted as a whole (maybe more than
      # one line, but they're always complete)
      return (self.host, line.strip())

  def fileno(self):
    '''
    Return file descriptor for ``poll()``
    '''
    return self.conn.fileno()

#-----------------------------------------------------------------------------

class UDP:
  '''
  Listening UDP socket.
  '''
  def __init__(self, host, port):
    '''
    :param host: bind address
    :type host: string or ``None``
    :param port: bind address
    :type port: integer
    '''
    self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if host is not None:
      self.conn.bind((host, port))
    else:
      self.conn.bind(('', port))

  def readline(self):
    '''
    :return: ``(host, string)``

    Read a single line sent to this port.
    '''
    # XXX: no EOF is expected here
    (line, (host, port)) = self.conn.recvfrom(16384)
    # TODO: resolve hostname (some cache maybe?)
    return (host, line.strip())

  def fileno(self):
    '''
    Return file descriptor for ``poll()``
    '''
    return self.conn.fileno()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
