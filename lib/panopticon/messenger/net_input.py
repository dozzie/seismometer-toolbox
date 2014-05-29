#!/usr/bin/python
'''
Network (and network-like) input: TCP, UDP, UNIX, stdin.

.. autoclass:: Poll
   :members:

.. autoclass:: ListenSTDIN
   :members:

.. autoclass:: ListenTCP
   :members:

.. autoclass:: TCPConnection
   :members:

.. autoclass:: ListenUDP
   :members:

.. autoclass:: ListenUNIX
   :members:

'''
#-----------------------------------------------------------------------------

import sys
import os
import socket
import panopticon.poll
import Queue

#-----------------------------------------------------------------------------

#   * socket aggregator (single poll(), returns one line at time)
#     * TCP sockets
#     * UDP sockets
#     * UNIX sockets (SOCK_DGRAM)
#     * hostname: for future: DNS cache; for now: IP address
#   * protocol parser
#     * JSON
#     * Graphite (tag value timestamp)
#     * Graphite-like (tag state severity timestamp)
#     * timestamp == "N" means now
#     * value == "U" means undefined
#     * drop non-conforming messages

#-----------------------------------------------------------------------------

class ListenSTDIN:
  '''
  Socket-like class for reading from standard input.
  '''
  def __init__(self):
    pass # nothing to do here

  def readline(self):
    line = sys.stdin.readline()
    if line == '':
      return None
    else:
      return line.strip()

  def fileno(self):
    return sys.stdin.fileno()

#-----------------------------------------------------------------------------

class TCPConnection:
  '''
  TCP connection reader.
  '''
  def __init__(self, conn):
    self.conn = conn

  def __del__(self):
    self.close()

  def close(self):
    if self.conn is not None:
      self.conn.close()
      self.conn = None

  def readline(self):
    line = self.conn.recv(16384)
    if line == '':
      return None
    else:
      # XXX: assume the line is always transmitted as a whole (maybe more than
      # one line, but they're always complete)
      return line.strip()

  def fileno(self):
    return self.conn.fileno()

class ListenTCP:
  '''
  Listening TCP socket. Not intended for reading itself.
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
    (client, addr) = self.conn.accept()
    return TCPConnection(client)

  def fileno(self):
    return self.conn.fileno()

#-----------------------------------------------------------------------------

class ListenUDP:
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
    # XXX: no EOF is expected here
    line = self.conn.recv(16384)
    return line.strip()

  def fileno(self):
    return self.conn.fileno()

#-----------------------------------------------------------------------------

class ListenUNIX:
  '''
  Listening UDP datagram socket.
  '''
  def __init__(self, path):
    '''
    :param path: bind address
    :type path: string
    '''
    self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.conn.bind(path)
    self.path = os.path.abspath(path)

  def __del__(self):
    self.conn.close()
    os.unlink(self.path)

  def readline(self):
    # XXX: no EOF is expected here
    line = self.conn.recv(16384)
    return line.strip()

  def fileno(self):
    return self.conn.fileno()

#-----------------------------------------------------------------------------

class Poll:
  '''
  Reading socket aggregator.
  '''
  def __init__(self):
    self.poll = panopticon.poll.Poll()
    self.queue = Queue.Queue()

  def add(self, sock):
    '''
    Add new socket to poll list.
    '''
    self.poll.add(sock)

  def remove(self, sock):
    '''
    Remove socket from poll list.
    '''
    self.poll.remove(sock)

  def readline(self):
    '''
    Read single line from all the sockets from poll list.
    '''
    # XXX: in any given poll there could be just TCP connection attempts and
    # closed sockets with no incoming data
    while self.queue.empty():
      for sock in self.poll.poll(-1): # wait for any input
        if isinstance(sock, ListenTCP):
          # TCP connection attempt, add client to poll and skip reading
          client = sock.accept()
          self.add(client)
          continue

        line = sock.readline()
        if line is not None:
          # some data (maybe multiline)
          for l in line.split('\n'):
            self.queue.put(l)
        else:
          # EOF, remove the socket from poll
          self.remove(sock)

    # loop ended, so there must be anything in the queue
    return self.queue.get()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
