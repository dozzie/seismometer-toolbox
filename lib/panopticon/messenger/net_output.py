#!/usr/bin/python

import socket
import json
import sys
import spool

#-----------------------------------------------------------------------------

#   * message sender
#     * TCP
#     * TCP/SJCP
#     * hides connection errors by spooling messages

#-----------------------------------------------------------------------------

class STDOUTSender:
  def __init__(self):
    pass

  def send(self, message):
    line = json.dumps(message) + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()

#-----------------------------------------------------------------------------

class TCPSender:
  def __init__(self, address, spooler = None):
    (host, port) = address.split(':')
    self.host = host
    self.port = int(port)
    self.conn = None
    if spooler is None:
      self.spooler = spool.MemorySpooler()
    else:
      self.spooler = spooler

  def send(self, message):
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
    line = self.spooler.peek()
    while line is not None:
      if self.write(line):
        self.spooler.drop_one()
        line = self.spooler.peek()
      else:
        return False
    return True

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
      conn = socket.socket()
      conn.connect((self.host, self.port))
      self.conn = conn
      return True
    except socket.error:
      return False

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
