#!/usr/bin/python

#-----------------------------------------------------------------------------

#   * Graphite tag matcher
#     * services = foo bar, baz, /.../
#                  indented further_text
#     * /regexp/:host.(services):service.*:aspect
#     * regexps are anchored (^$)
#     * default: host=$origin, aspect=$tag

#-----------------------------------------------------------------------------

class TagMatcher:
  def __init__(self, config = None):
    self.config = config
    self.reload()

  def match(self, tag):
    # TODO: implement me
    return ({}, tag) # (location, aspect)

  def reload(self):
    pass # TODO

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
