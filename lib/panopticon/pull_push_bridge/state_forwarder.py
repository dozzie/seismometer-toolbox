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

#-----------------------------------------------------------------------------

class PullPushBridge:
  def __init__(self, options):
    (self.host, self.port, self.channel) = options.destination.split(":", 2)
    self.port = int(self.port)
    self.conn = streem.Streem(self.host, self.port)
    self.conn.register(self.channel)

  def send(self, message):
    try:
      # FIXME: hardcoded for ModMon::Event v=2
      if (message.get('v') == 2) and 'value' in message['event']['state']:
        self.conn.submit(message)
    except KeyError:
      pass # it's OK to not find a key in hash

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
