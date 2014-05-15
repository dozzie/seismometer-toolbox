#!/usr/bin/python
'''
message printer plugin
----------------------

This plugin is mainly useful for debugging. It just prints the incoming
message to *STDOUT* as a single-line JSON.

Options:

   * :option:`--destination` -- option is ignored

'''
#-----------------------------------------------------------------------------

import json
import sys

#-----------------------------------------------------------------------------

class PullPushBridge:
  def __init__(self, options):
    pass

  def send(self, message):
    sys.stdout.write(json.dumps(message.to_dict(), sort_keys = True) + '\n')
    sys.stdout.flush()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
