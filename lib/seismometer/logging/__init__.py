#!/usr/bin/python

#-----------------------------------------------------------------------------

try:
  # Python 2.7+
  from logging.config import dictConfig
except ImportError:
  # older Python, use PT's copy of dictConfig()
  from logging_config import dictConfig

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
