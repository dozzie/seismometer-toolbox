#!/usr/bin/python
'''
Simple line message parser.

.. autofunction:: parse_line

'''
#-----------------------------------------------------------------------------

import os
import re
import json
import panopticon.message

_GRAPHITE_LINE = re.compile(
  r'^(?P<tag>(?:[a-zA-Z0-9_-]+\.)*[a-zA-Z0-9_-]+)[ \t]+(?:'
    r'(?P<value>-?[0-9.]+|U)'
    r'|'
    r'(?P<state>[a-zA-Z0-9_]+)[ \t]+(?P<severity>expected|warning|critical)'
  r')[ \t]+(?P<time>[0-9.]+)$'
)

#-----------------------------------------------------------------------------

def parse_line(host, line):
  '''
  :return: loaded JSON, ``(host, tag, value, time)`` or None if couldn't parse
    the line
  :rtype: dict, 4-tuple or ``None``

  Parse line and convert it to some usable data.

  ``value`` in 4-tuple form is a ``(state, severity)`` tuple for state or
  float/int/``None`` for metric.
  '''
  if line[0] == '{': # JSON
    try:
      return json.loads(line)
    except ValueError:
      return None

  match = _GRAPHITE_LINE.match(line)
  if match is None: # not a Graphite(like) protocol
    return None

  match = match.groupdict()

  if host in (None, '127.0.0.1', 'localhost', 'localhost.localdomain'):
    host = os.uname()[1]

  timestamp = int(match['time'])

  # TODO: use tag matcher
  aspect = match['tag']
  location = { 'host': host }

  if match['value'] is None: # match['state'] + match['severity']
    message = panopticon.message.Message(
      aspect = aspect, location = location, time = timestamp,
      state = match['state'], severity = match['severity']
    )
  elif match['value'] == 'U':
    message = panopticon.message.Message(
      aspect = aspect, location = location, time = timestamp,
      value = None
    )
  elif '.' in match['value']: # float
    message = panopticon.message.Message(
      aspect = aspect, location = location, time = timestamp,
      value = float(match['value'])
    )
  else:
    message = panopticon.message.Message(
      aspect = aspect, location = location, time = timestamp,
      value = int(match['value'])
    )

  return message.to_dict()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
