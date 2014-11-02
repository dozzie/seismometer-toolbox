#!/usr/bin/python

import sys
import optparse
import panopticon.messenger
import panopticon.messenger

#-----------------------------------------------------------------------------
# command line options {{{

parser = optparse.OptionParser(
  usage = "%prog [options]",
  description = "TODO"
)

parser.add_option(
  "--destination", "--dest", dest = "destination",
  action = "append", default = [],
  help = "where to send messages",
  metavar = "ADDR",
)
parser.add_option(
  "--source", "--src", dest = "source",
  action = "append", default = [],
  help = "where to read/expect messages from",
  metavar = "ADDR",
)
parser.add_option(
  "--tagfile", dest = "tag_file",
  help = "definitions used to convert Graphite-like tags to \"location\" for"
         " Panopticon Message",
  metavar = "TAGFILE",
)
parser.add_option(
  "--spool", dest = "spool",
  help = "directory to spool messages in case of network problems",
  metavar = "SPOOLDIR",
)
parser.add_option(
  "--max-spool", dest = "max_spool",
  help = "how much to keep in spool before dropping the earliest messages"
         " (in bytes; allowed suffixes are 'k' and 'M')",
  metavar = "SIZE",
)
parser.add_option(
  "--logging", dest = "logging",
  help = "YAML/JSON file with logging configuration",
  metavar = "FILE",
)

# }}}
#-----------------------------------------------------------------------------

(options, args) = parser.parse_args()

if len(args) > 0:
  parser.print_help()
  sys.exit(1)

if len(options.source) == 0:
  options.source = ["stdin"]

if len(options.destination) == 0:
  options.destination = ["stdout"]

#-----------------------------------------------------------------------------
# --source options parsing {{{

def parse_source(source):
  if source == "stdin":
    import panopticon.messenger.net_input.stdin
    return panopticon.messenger.net_input.stdin.STDIN()

  if source.startswith("tcp:"):
    if ":" in source[4:]:
      (host, port) = source[4:].split(":")
      port = int(port)
    else:
      host = None
      port = int(source[4:])
    import panopticon.messenger.net_input.inet
    return panopticon.messenger.net_input.inet.TCP(host, port)

  if source.startswith("udp:"):
    if ":" in source[4:]:
      (host, port) = source[4:].split(":")
      port = int(port)
    else:
      host = None
      port = int(source[4:])
    import panopticon.messenger.net_input.inet
    return panopticon.messenger.net_input.inet.UDP(host, port)

  if source.startswith("unix:"):
    path = source[5:]
    import panopticon.messenger.net_input.unix
    return panopticon.messenger.net_input.unix.UNIX(path)

  import json
  params = json.loads(source)
  import panopticon.messenger.net_input.plugin
  return panopticon.messenger.net_input.plugin.Plugin(params['class'], params)

# }}}
#-----------------------------------------------------------------------------
# --destination options parsing {{{

def parse_destination(destination):
  if destination == "stdout":
    import panopticon.messenger.net_output.stdout
    return panopticon.messenger.net_output.stdout.STDOUT()

  if destination.startswith("tcp:"):
    (host, port) = destination[4:].split(":")
    port = int(port)
    import panopticon.messenger.net_output.inet
    return panopticon.messenger.net_output.inet.TCP(host, port)

  if destination.startswith("udp:"):
    (host, port) = destination[4:].split(":")
    port = int(port)
    import panopticon.messenger.net_output.inet
    return panopticon.messenger.net_output.inet.UDP(host, port)

  if destination.startswith("unix:"):
    path = destination[5:]
    import panopticon.messenger.net_output.unix
    return panopticon.messenger.net_output.unix.UNIX(path)

  import json
  params = json.loads(destination)
  import panopticon.messenger.net_output.plugin
  return panopticon.messenger.net_output.plugin.Plugin(params['class'], params)

# }}}
#-----------------------------------------------------------------------------

sources      = [parse_source(o)      for o in options.source]
destinations = [parse_destination(o) for o in options.destination]

reader = panopticon.messenger.net_input.Reader()
writer = panopticon.messenger.net_output.Writer()

for s in sources:
  reader.add(s)
for d in destinations:
  writer.add(d)

#-----------------------------------------------------------------------------

# TODO:
#   * signal handlers:
#     * SIGPIPE: SIG_IGN
#     * SIGHUP: reload tag patterns
#     * SIGUSR1: reload logging config

#-----------------------------------------------------------------------------
# main loop

try:
  while True:
    message = reader.read()
    writer.write(message)
except KeyboardInterrupt:
  pass
except panopticon.messenger.net_input.EOF:
  # this is somewhat expected: all the input descriptors are closed (e.g. only
  # STDIN was specified)
  pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
