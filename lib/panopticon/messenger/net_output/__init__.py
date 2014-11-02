#!/usr/bin/python
'''
Sending a message to bunch of ``net_output`` sockets.

.. autoclass:: Writer
   :members:

'''
#-----------------------------------------------------------------------------

import json
import signal

#-----------------------------------------------------------------------------

class Writer:
  def __init__(self):
    self.outputs = []

    # setup SIGALRM to be called every N seconds and try flushing all the
    # outputs (reconnecting to the remote if necessary)
    flush_interval = 10
    def alarm_handler(sig, stack):
      for o in self.outputs:
        o.flush()
      signal.alarm(flush_interval)
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(flush_interval)

  def add(self, output):
    self.outputs.append(output)

  def write(self, message):
    for o in self.outputs:
      o.send(message)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
