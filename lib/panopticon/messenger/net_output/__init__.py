#!/usr/bin/python
'''
Sending a message to bunch of ``net_output`` sockets.

.. autoclass:: Writer
   :members:

'''
#-----------------------------------------------------------------------------

import json

#-----------------------------------------------------------------------------

class Writer:
  def __init__(self):
    self.outputs = []

  def add(self, output):
    self.outputs.append(output)

  def write(self, message):
    for o in self.outputs:
      o.send(message)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
