#!/usr/bin/python

import os
import re
import json
import seismometer.input
import seismometer.message

#-----------------------------------------------------------------------------

class MessengerReader(seismometer.input.Reader):
    '''
    Network reader accepting JSON and Graphite-like messages.

    This reader accepts three data formats, each in its own line: JSON hash,
    Graphite/Carbon (``tag value timestamp``) or Graphite-like state (``tag
    state severity timestamp``). The latter two are converted to Seismometer
    Message structure.

    Some notes:
      * severity must be equal to ``"expected"``, ``"warning"`` or
        ``"critical"``
      * timestamp is an integer (epoch time)
      * value for metric is integer, float in non-scientific notation or
        ``"U"`` ("undefined")
    '''

    _GRAPHITE_LINE = re.compile(
        r'^(?P<tag>(?:[a-zA-Z0-9_-]+\.)*[a-zA-Z0-9_-]+)[ \t]+(?:'
            r'(?P<value>-?[0-9.]+|U)'
            r'|'
            r'(?P<state>[a-zA-Z0-9_]+)[ \t]+(?P<severity>expected|warning|critical)'
        r')[ \t]+(?P<time>[0-9.]+)$'
    )

    def __init__(self, tag_matcher):
        super(MessengerReader, self).__init__()
        self.tag_matcher = tag_matcher

    def parse_line(self, host, line):
        '''
        :return: dict, possibly structured after
           :class:``seismometer.message.Message``

        Parse line and convert it to some usable data.
        '''
        if line == '':
            return None

        if line[0] == '{': # JSON
            try:
                return json.loads(line)
            except ValueError:
                return None

        match = MessengerReader._GRAPHITE_LINE.match(line)
        if match is None: # not a Graphite(like) protocol
            return None

        match = match.groupdict()

        if host in (None, '127.0.0.1', 'localhost', 'localhost.localdomain'):
            host = os.uname()[1]

        timestamp = int(match['time'])

        (aspect, location) = self.tag_matcher.match(match['tag'])

        if match['value'] is None: # match['state'] + match['severity']
            message = seismometer.message.Message(
                aspect = aspect, location = location, time = timestamp,
                state = match['state'], severity = match['severity']
            )
        elif match['value'] == 'U':
            message = seismometer.message.Message(
                aspect = aspect, location = location, time = timestamp,
                value = None
            )
        elif '.' in match['value']: # float
            message = seismometer.message.Message(
                aspect = aspect, location = location, time = timestamp,
                value = float(match['value'])
            )
        else:
            message = seismometer.message.Message(
                aspect = aspect, location = location, time = timestamp,
                value = int(match['value'])
            )

        return message.to_dict()

#-----------------------------------------------------------------------------
# vim:ft=python
