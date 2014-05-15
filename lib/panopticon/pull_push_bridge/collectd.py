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
    if len(message) == 0:
      return

    try:
      host = message.location['host']
      time = message.time
      for n in sorted(message):
        name = PullPushBridge.encode_location(
          message.location, message.aspect, n
        )
        if message[n] is not None:
          value = message[n].value
        else:
          value = 'U'

        if message.interval is not None:
          line = "PUTVAL %s/panopticon/gauge-%s interval=%d %d:%s\n" % \
                 (host, name, message.interval, time, value)
        else:
          line = "PUTVAL %s/panopticon/gauge-%s %d:%s\n" % \
                 (host, name, time, value)

        self.socket.send(line)
        self.socket.recv(256) # discard (FIXME: detect submission error)
    except KeyError:
      pass # don't die, do nothing

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
