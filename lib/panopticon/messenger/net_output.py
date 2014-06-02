#!/usr/bin/python

import socket
import json

#-----------------------------------------------------------------------------

#   * message sender
#     * TCP
#     * TCP/SJCP
#     * hides connection errors by spooling messages

#-----------------------------------------------------------------------------

class TCPSender:
  def __init__(self, address, spooler):
    (host, port) = ':'.split(address)
    self.host = host
    self.port = int(port)
    self.conn = None
    self.spooler = spooler

  def send(self, message):
    line = json.dumps(message)

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
      else:
        return False

  def write(self, line):
    try:
      self.conn.send(line)
      return True
    except socket.error, e:
      # lost connection
      return False

  def is_connected(self):
    # TODO: better check
    return (self.conn is None)

  def repair_connection(self):
    self.conn = socket.socket()
    self.conn.connect((self.host, self.port))

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
