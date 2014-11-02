#!/usr/bin/python
'''
Reading from a bunch of ``net_input`` sockets.

.. autoclass:: Reader
   :members:

.. autoclass:: Poll
   :members:

.. autoexception:: EOF
   :members:

'''
#-----------------------------------------------------------------------------

import os
import panopticon.poll
import Queue

from _connection_socket import ConnectionSocket
import parser

#-----------------------------------------------------------------------------

class EOF(Exception):
  '''
  EOF condition on all the inputs.
  '''
  pass

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
    if self.poll.empty():
      raise EOF()

  def readline(self):
    '''
    :return: originating host and line received
    :rtype: tuple (string, string)

    Read single line from all the sockets from poll list.
    '''
    # XXX: in any given poll there could be just TCP connection attempts and
    # closed sockets with no incoming data
    while self.queue.empty():
      for sock in self.poll.poll(-1): # wait for any input
        if isinstance(sock, ConnectionSocket):
          # connection attempt, add client to poll and skip reading
          client = sock.accept()
          self.add(client)
          continue

        (host, line) = sock.readline()
        if line is not None:
          # some data (maybe multiline)
          for l in line.split('\n'):
            self.queue.put((host, l.strip()))
        else:
          # EOF, remove the socket from poll
          self.remove(sock)

    # loop ended, so there must be anything in the queue
    return self.queue.get()

#-----------------------------------------------------------------------------

class Reader:
  '''
  Network reader, polling for a line and converting it to proper message.

  This reader accepts three data formats, each in its own line: JSON hash,
  Graphite/Carbon (``tag value timestamp``) or Graphite-like state
  (``tag state severity timestamp``). The latter two are converted to
  Panopticon Message.

  Some notes:
    * severity must be equal to ``"expected"``, ``"warning"`` or ``"critical"``
    * timestamp is an integer (epoch time)
    * value for metric is integer, float in non-scientific notation or ``"U"``
      ("undefined")
  '''
  def __init__(self):
    self.poll = Poll()

  def add(self, sock):
    '''
    Add a socket to poll list.
    '''
    self.poll.add(sock)

  def read(self):
    '''
    :rtype: dict

    Read a message from polled sockets.
    '''
    # try reading and parsing until a good message is produced
    while True:
      (host, line) = self.poll.readline()
      message = parser.parse_line(host, line)

      if message is not None:
        return message

      # else (message is None): try reading next message


#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
