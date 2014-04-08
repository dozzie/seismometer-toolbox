#!/usr/bin/python
#
# instead of having separate hack-state-forwarder.py I could just use this
# plugin to pull-push-bridge
#

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
      # FIXME: hardcoded for ModMon::Event v=1
      if (message.get('v') == 1) and 'value' in message['event']['state']:
        self.conn.submit(message)
    except KeyError:
      pass # it's OK to not find a key in hash

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
