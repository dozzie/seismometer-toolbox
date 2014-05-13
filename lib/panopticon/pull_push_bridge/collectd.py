#!/usr/bin/python
'''
collectd forwarder plugin
-------------------------

This plugin forwards metrics to `collectd <http://collectd.org/>`_.

Metric name is composed of ``location.service``, aspect name and value name.
Metrics coming from a host have following pattern:

.. code-block:: none

   <hostname>/panopticon/gauge-<service>+<aspect>+<value>

Options:

   * :option:`--destination` ``<socket_path>``

     Path to socket (collectd's plugin :manpage:`collectd-unixsock(5)`).

'''
#-----------------------------------------------------------------------------

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
      # FIXME: hardcoded for ModMon::Event v=2
      if (message.get('v') == 2) and 'vset' in message['event']:
        value_set = message['event']['vset']
        host = message['location']['host']
        time = message['time']
        for n in sorted(value_set):
          name = PullPushBridge.encode_location(
            message['location'], message['event']['name'], n
          )
          if value_set[n]['value'] is not None:
            value = value_set[n]['value']
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
