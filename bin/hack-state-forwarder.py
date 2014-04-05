#!/usr/bin/python
#
# Forwarder of messages that are of Panopticon's structure and that carry
# a state information ("OK"/"warning").
#
# This forwarder is to be dropped once Streem is smart enough to do it on its
# own and preserve queries between restarts.
#
#-----------------------------------------------------------------------------

import optparse
import streem

#-----------------------------------------------------------------------------
# parse command line options

parser = optparse.OptionParser(
  usage = "%prog" \
          " [--source=host:port:channel]" \
          " [--destination=host:port:channel]",
)

parser.add_option(
  "--source", dest = "source", default = "stdout",
  help = "source of messages with state (host:port:channel or stdout;"
         " stdout is the default)",
  metavar = "SOURCE",
)
parser.add_option(
  "--destination", dest = "destination", default = "stdout",
  help = "destination of messages with state (host:port:channel or stdout;"
         " stdout is the default)",
  metavar = "TARGET",
)

(options, args) = parser.parse_args()

if options.source is None or options.destination is None:
  parser.print_help()
  sys.exit(1)

#-----------------------------------------------------------------------------
# check if the message qualifies to being forwarded

def has_state(msg):
  # FIXME: hardcoded for ModMon::Event v=1
  try:
    return (msg.get('v') == 1) and 'value' in msg['event']['state']
  except KeyError:
    return False

#-----------------------------------------------------------------------------
# main loop

(host, port, channel) = options.source.split(":", 2)
channel_in = streem.Streem(host, int(port))
channel_in.subscribe(channel)

(host, port, channel) = options.destination.split(":", 2)
channel_out = streem.Streem(host, int(port))
channel_out.register(channel)

try:
  while True:
    m = channel_in.receive()
    if has_state(m):
      channel_out.submit(m)
except KeyboardInterrupt:
  pass

#-----------------------------------------------------------------------------
# vim:ft=python
