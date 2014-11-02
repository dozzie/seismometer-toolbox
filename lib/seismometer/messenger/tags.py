#!/usr/bin/python
'''
Tag matcher for Graphite-like monitoring input. Intended to make location and
aspect name out of metric path.

.. autoclass:: TagMatcher
   :members:

'''
#-----------------------------------------------------------------------------

#   * Graphite tag matcher
#     * services = foo bar, baz, /.../
#                  indented further_text
#     * /regexp/:host.(services):service.*:aspect
#     * regexps are anchored (^$)
#     * default: host=$origin, aspect=$tag

#-----------------------------------------------------------------------------

class TagMatcher:
  '''
  Tag matcher class.
  '''
  def __init__(self, config = None):
    '''
    :param config: configuration file with tag patterns
    '''
    self.config = config
    self.reload()

  def match(self, tag):
    '''
    :return: location and aspect name
    :rtype: tuple (dict, string)

    Match tag against patterns from configuration file.
    '''
    # TODO: implement me
    return ({}, tag) # (location, aspect)

  def reload(self):
    '''
    Reload configuration file.
    '''
    pass # TODO

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
