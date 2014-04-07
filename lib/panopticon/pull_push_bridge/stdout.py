#!/usr/bin/python

import json

#-----------------------------------------------------------------------------

class PullPushBridge:
  def __init__(self, options):
    pass

  def send(self, message):
    print json.dumps(message, sort_keys = True)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
