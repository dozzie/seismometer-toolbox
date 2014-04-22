#!/usr/bin/python

import json
import sys

#-----------------------------------------------------------------------------

class PullPushBridge:
  def __init__(self, options):
    pass

  def send(self, message):
    sys.stdout.write(json.dumps(message, sort_keys = True) + '\n')
    sys.stdout.flush()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
