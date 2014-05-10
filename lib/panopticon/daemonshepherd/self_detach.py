#!/usr/bin/python

import os
import sys

#-----------------------------------------------------------------------------

def detach(new_cwd = None):
  if os.fork() == 0:
    if new_cwd is not None:
      os.chdir(new_cwd)
    child_process()
  else:
    parent_process()

def child_process():
  # replace STDIN, STDOUT and STDERR
  sys.stdin = open('/dev/null')
  sys.stdout = sys.stderr = open('/dev/null', 'w')

def parent_process():
  # TODO: wait for child to acknowledge success
  sys.exit(0)

def detach_succeeded():
  # TODO: implement me
  pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
