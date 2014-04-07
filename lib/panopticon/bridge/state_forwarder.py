#!/usr/bin/python

# instead of having separate hack-state-forwarder.py I could just use this
# plugin to pull-push-bridge

class PullPushBridge:
  def __init__(self, options):
    self.collectd_socket = options.destination
    #self.socket = 

  def send(self, message):
    pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
