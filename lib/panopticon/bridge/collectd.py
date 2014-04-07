#!/usr/bin/python

# PUTVAL $host/$plugin/$type-$instance $time:$value
# $value, $value_name -- from vset
# $host = $m{location}{host}
# $plugin = "streem"
# $type = "gauge"
# $instance = sprintf "%s+%s+%s",
#                     $m{location}{service}, $m{event}{name}, $value_name

class PullPushBridge:
  def __init__(self, options):
    self.collectd_socket = options.destination
    #self.socket = 

  def send(self, message):
    pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
