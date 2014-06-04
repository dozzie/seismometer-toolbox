#!/usr/bin/python
'''
Network message senders.

.. autoclass:: STDOUTSender
   :members:

.. autoclass:: TCPSender
   :members:

.. autoclass:: StreemSender
   :members:
   :inherited-members:

'''
#-----------------------------------------------------------------------------

import socket
import json
import sys
import spool

#-----------------------------------------------------------------------------
#
# TODO: extract common code from StreemSender and TCPSender
#
#-----------------------------------------------------------------------------

class STDOUTSender:
  '''
  Sender printing message to STDOUT.
  '''
  def __init__(self):
    pass

  def send(self, message):
    '''
    :param message: message to print

    Print single message.
    '''
    line = json.dumps(message) + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()

#-----------------------------------------------------------------------------

class TCPSender(object):
  '''
  Sender passing message to another messenger (or anything accepting raw JSON
  lines through TCP).
  '''
  def __init__(self, host, port, spooler = None):
    '''
    :param host: address to send data to
    :param port: address to send data to
    :param spooler: spooler object (defaults to :class:`spool.MemorySpooler`
      with no limits)
    '''
    self.host = host
    self.port = port
    self.conn = None
    if spooler is None:
      self.spooler = spool.MemorySpooler()
    else:
      self.spooler = spooler

  def send(self, message):
    '''
    :param message: message to send

    Send single message.

    In case of connectivity errors message will be spooled and sent later.
    '''
    line = json.dumps(message) + "\n"

    if not self.is_connected() and not self.repair_connection():
      # lost connection, can't repair it at the moment
      self.spooler.spool(line)
      return

    # self.is_connected()
    if not self.send_pending() or not self.write(line):
      # didn't send all the pending lines -- make the current one pending, too
      # didn't send the current line -- make it pending
      self.spooler.spool(line)

  def send_pending(self):
    '''
    Send all pending messages.
    '''
    line = self.spooler.peek()
    while line is not None:
      if self.write(line):
        self.spooler.drop_one()
        line = self.spooler.peek()
      else:
        return False
    return True

  def write(self, line):
    '''
    :return: ``True`` when line was sent successfully, ``False`` when problems
      occurred

    Write single line to TCP socket.
    '''
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
    '''
    Check if the object has connection to the remote side.
    '''
    # FIXME: better check
    return (self.conn is not None)

  def repair_connection(self):
    '''
    :return: ``True`` if connected successfully, ``False`` otherwise.

    Try connecting to the remote side.
    '''
    try:
      conn = socket.socket()
      conn.connect((self.host, self.port))
      self.conn = conn
      return True
    except socket.error:
      return False

#-----------------------------------------------------------------------------

class StreemSender(TCPSender):
  '''
  Sender passing message to Streem.
  '''
  def __init__(self, host, port, channel, spooler = None):
    '''
    :param address: address to send data to (``host:port:channel``)
    :param spooler: spooler object (defaults to :class:`spool.MemorySpooler`
      with no limits)
    '''
    super(StreemSender, self).__init__(host, port, spooler)
    self.channel = channel

  def write(self, line):
    '''
    :return: ``True`` when line was sent successfully, ``False`` when problems
      occurred

    Write single line to TCP socket.
    '''
    # NOTE: `line' is NL-terminated
    request = '{"submit": %s}\n' % (line[0:-1],)
    try:
      self.conn.send(request)
      if self.read_ack():
        return True
      else: # unlikely
        self.conn.close()
        self.conn = None
        return False
    except socket.error:
      # lost connection
      self.conn = None
      return False

  def repair_connection(self):
    '''
    :return: ``True`` if connected successfully, ``False`` otherwise.

    Try connecting to the remote side.
    '''
    # first, setup TCP connection
    if super(StreemSender, self).repair_connection():
      # then, register the channel
      if self.register_channel(self.channel):
        return True
      else:
        self.conn.close()
        self.conn = None
        return False
    return False

  def register_channel(self, channel):
    '''
    Register channel which this connection will send messages to.
    '''
    print "registering channel %s" % (channel,)
    reg_request = { "register": channel }
    # FIXME: defend against network problems at this point (they're unlikely,
    # though)
    self.conn.send(json.dumps(reg_request) + "\n")
    return self.read_ack()

  def read_ack(self):
    '''
    :return: ``True`` if acknowledgement carried success, ``False`` otherwise

    Read acknowledgement response.
    '''
    print "reading ACK"
    response = self.conn.recv(1024) # assume this will be just one line
    if response == '':
      return False
    response = json.loads(response)
    return (response.get("status") == "ok")

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
