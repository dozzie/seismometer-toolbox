#!/usr/bin/python

import os

#-----------------------------------------------------------------------------

PLUGINS = set([
  f[0:-3]
  for f in os.listdir(os.path.dirname(__file__))
  if f.endswith(".py") and not f.startswith('_')
])

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
