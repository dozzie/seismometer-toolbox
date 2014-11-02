#!/usr/bin/python
'''
state forwarder plugin
----------------------

This plugin forwards messages carrying state (see :doc:`/message`) back to
Streem, to a different channel.

Options:

   * :option:`--destination` ``<host>:<port>:<channel>``

     Streem address.

'''
#-----------------------------------------------------------------------------

import streem
from optparse import make_option

#-----------------------------------------------------------------------------

class PullPushBridge:
  options = [
    make_option(
      "--destination", dest = "destination",
      help = "destination channel of messages (host:port:channel)",
      metavar = "ADDR",
    ),
  ]

  def __init__(self, options):
    (self.host, self.port, self.channel) = options.destination.split(":", 2)
    self.port = int(self.port)
    self.conn = streem.Streem(self.host, self.port)
    self.conn.register(self.channel)

  def send(self, message):
    if message.state is not None:
      self.conn.submit(message.to_dict())

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
