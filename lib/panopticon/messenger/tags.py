#!/usr/bin/python

#-----------------------------------------------------------------------------

#   * Graphite tag matcher
#     * services = foo bar, baz, /.../
#                  indented further_text
#     * /regexp/:host.(services):service.*:aspect
#     * regexps are anchored (^$)
#     * default: host=$origin, aspect=$tag

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
