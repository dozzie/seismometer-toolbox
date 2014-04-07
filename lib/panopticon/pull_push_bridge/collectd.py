#!/usr/bin/python

import socket
import re

#-----------------------------------------------------------------------------

class PullPushBridge:
  NON_WORD = re.compile(r'[^a-zA-Z0-9_.]')

  def __init__(self, options):
    self.collectd_socket = options.destination
    self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    self.socket.connect(self.collectd_socket)

  @staticmethod
  def encode_location(location, aspect_name, value_name):
    # FIXME: this naming scheme is very inflexible
    return "%s+%s+%s" % (
      PullPushBridge.NON_WORD.sub("_", location['service']),
      PullPushBridge.NON_WORD.sub("_", aspect_name),
      PullPushBridge.NON_WORD.sub("_", value_name),
    )

  def send(self, message):
    try:
      # FIXME: hardcoded for ModMon::Event v=1
      if (message.get('v') == 1) and 'vset' in message['event']:
        host = message['location']['host']
        time = message['time']
        for n in sorted(message['event']['vset']['value']):
          name = PullPushBridge.encode_location(
            message['location'], message['event']['name'], n
          )
          if message['event']['vset']['value'][n] is not None:
            value = message['event']['vset']['value'][n]
          else:
            value = 'U'
          self.socket.send(
            "PUTVAL %s/panopticon/gauge-%s %d:%s\n" % (host, name, time, value)
          )
          self.socket.recv(256) # discard (FIXME: detect submission error)
    except KeyError:
      pass # don't die, do nothing

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
