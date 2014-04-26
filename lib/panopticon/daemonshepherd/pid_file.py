#!/usr/bin/python

import os

#-----------------------------------------------------------------------------

class PidFile:
  def __init__(self, filename):
    self.filename = os.path.abspath(filename)
    self.fd = open(self.filename, 'w', 0) # TODO: atomic create-or-fail
    self.pid = None
    self.remove_on_close = False
    self.update()

  def claim(self):
    self.remove_on_close = True

  def update(self):
    if self.fd is None:
      return # or raise an error?
    self.pid = os.getpid()
    self.fd.seek(0)
    self.fd.write("%d\n" % (self.pid))
    self.fd.truncate()

  def close(self):
    self.fd.close()
    self.fd = None

  def __del__(self):
    if self.fd is None:
      # do nothing if closed already
      return

    self.fd.close()
    if self.remove_on_close and self.pid == os.getpid():
      # only remove the file if owner
      os.unlink(self.filename)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
