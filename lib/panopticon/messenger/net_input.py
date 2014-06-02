#!/usr/bin/python
'''
Network (and network-like) input: TCP, UDP, UNIX, stdin.

.. autoclass:: Reader
   :members:

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
import panopticon.message
import Queue
import json
import time

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
      return (None, None)
    else:
      return (None, line.strip())

  def fileno(self):
    return sys.stdin.fileno()

#-----------------------------------------------------------------------------

class TCPConnection:
  '''
  TCP connection reader.
  '''
  def __init__(self, conn, host):
    self.conn = conn
    # TODO: resolve hostname (some cache maybe?)
    self.host = host

  def __del__(self):
    self.close()

  def close(self):
    if self.conn is not None:
      self.conn.close()
      self.conn = None

  def readline(self):
    line = self.conn.recv(16384)
    if line == '':
      return (None, None)
    else:
      # XXX: assume the line is always transmitted as a whole (maybe more than
      # one line, but they're always complete)
      return (self.host, line.strip())

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
    (client, (host, port)) = self.conn.accept()
    return TCPConnection(client, host)

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
    (line, (host, port)) = self.conn.recvfrom(16384)
    # TODO: resolve hostname (some cache maybe?)
    return (host, line.strip())

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
    return (None, line.strip())

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
    :return: originating host and line received
    :rtype: tuple (string, string)

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

import re
graphite_line = re.compile(
  r'^(?P<tag>(?:[a-zA-Z0-9_-]+\.)*[a-zA-Z0-9_-]+)[ \t]+(?:'
    r'(?P<value>-?[0-9.]+|U)'
    r'|'
    r'(?P<state>[a-zA-Z0-9_]+)[ \t]+(?P<severity>expected|warning|critical)'
  r')[ \t]+(?P<time>[0-9.]+|N)$'
)

def parse_line(host, line):
  '''
  :return: loaded JSON, ``(host, tag, value, time)`` or None if couldn't parse
    the line
  :rtype: dict, 4-tuple or ``None``

  Parse line and convert it to some usable data.

  ``value`` in 4-tuple form is a ``(state, severity)`` tuple for state or
  float/int/``None`` for metric.
  '''
  if line[0] == '{': # JSON
    try:
      return json.loads(line)
    except ValueError:
      return None

  match = graphite_line.match(line)
  if match is None: # not a Graphite(like) protocol
    return None

  match = match.groupdict()

  tag = match['tag']

  if match['time'] == 'N':
    timestamp = int(time.time())
  else:
    timestamp = int(match['time'])

  if match['value'] is None: # match['state'] + match['severity']
    value = (match['state'], match['severity'])
  elif match['value'] == 'U':
    value = None
  elif '.' in match['value']: # float
    value = float(match['value'])
  else:
    value = int(match['value'])

  if host in (None, '127.0.0.1', 'localhost', 'localhost.localdomain'):
    host = os.uname()[1]

  return (host, tag, value, timestamp)

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
    * timestamp is an integer (epoch time) or ``"N"`` ("now")
    * value for metric is integer, float in non-scientific notation or ``"U"``
      ("undefined")
  '''
  def __init__(self, tag_matcher = None):
    '''
    :param tag_matcher: tag to location+aspect converter
    '''
    if tag_matcher is not None:
      self.tag_matcher = tag_matcher
    else:
      import tags
      self.tag_matcher = tags.TagMatcher()
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
      message = parse_line(host, line)

      if message is None:
        # TODO: log this
        continue

      if isinstance(message, dict):
        return message

      (host, tag, value, timestamp) = message

      (location, aspect) = self.tag_matcher.match(tag)
      if "host" not in location:
        location["host"] = host

      if isinstance(value, tuple):
        message = panopticon.message.Message(
          aspect = aspect, location = location, time = timestamp,
          state = value[0], severity = value[1]
        )
      else: # float, int or None
        message = panopticon.message.Message(
          aspect = aspect, location = location, time = timestamp,
          value = value
        )
      return message.to_dict()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
