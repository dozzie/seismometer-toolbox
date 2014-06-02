#!/usr/bin/python

import sys
import optparse

#-----------------------------------------------------------------------------
# parse command line options

parser = optparse.OptionParser(
  usage = "%prog [options] LISTEN_ADDR ...",
  description = "Listen addresses have a form of tcp:PORT, tcp:BIND_ADDR:PORT,"
                " udp:PORT, udp:BIND_ADDR:PORT, unix:PATH (datagram socket)"
                " or \"-\" (STDIN)."
)

parser.add_option(
  "--destination", dest = "destination",
  help = "where to send messages (host:port for simple, line-based JSON"
         " or host:port:channel for Streem; default is to print messages to"
         " STDOUT)",
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

(options, args) = parser.parse_args()

if len(args) == 0:
  parser.print_help()
  sys.exit(1)

#-----------------------------------------------------------------------------
# verify `args' (listen specifications)

import re

net_re = re.compile(
  r'^(?P<proto>tcp|udp):(?:(?P<host>[^:]+):)?(?P<port>[0-9]+)$'
)
unix_re = re.compile(r'^(?P<proto>unix):(?:(?P<path>.+))$')

listen_spec = []
for a in args:
  if a == "-":
    listen_spec.append({'proto': 'stdin'})
    continue

  match = net_re.match(a)
  if match is None:
    match = unix_re.match(a)

  if match is None:
    parser.print_help()
    sys.exit(1)

  spec = match.groupdict()
  if spec.get('port') is not None:
    spec['port'] = int(spec['port'])

  listen_spec.append(spec)

#-----------------------------------------------------------------------------

from panopticon.messenger import net_input, tags

# TODO: custom plugin
tag_matcher = tags.TagMatcher(options.tag_file)
reader = net_input.Reader(tag_matcher)
for spec in listen_spec:
  if spec['proto'] == 'stdin':
    sock = net_input.ListenSTDIN()
  elif spec['proto'] == 'tcp':
    sock = net_input.ListenTCP(spec['host'], int(spec['port']))
  elif spec['proto'] == 'udp':
    sock = net_input.ListenUDP(spec['host'], int(spec['port']))
  elif spec['proto'] == 'unix':
    sock = net_input.ListenUNIX(spec['path'])

  reader.add(sock)

# TODO:
#   * signal handlers:
#     * SIGPIPE: SIG_IGN
#     * SIGHUP: reload tag patterns
#     * SIGUSR1: reload logging config
#   * fsync'd STDOUT (use in pipe)
#   * date +"foo.bar $VALUE %s" | messenger.py -

#-----------------------------------------------------------------------------
# main loop

from panopticon.messenger import net_output
if options.destination is None:
  # no spooler
  destination = net_output.STDOUTSender()
else:
  # TODO: add spooler
  destination = net_output.TCPSender(options.destination)

try:
  pass # TODO
  while True:
    message = reader.read()
    destination.send(message)
except KeyboardInterrupt:
  pass
except net_input.EOF:
  # this is somewhat expected: all the input descriptors are closed (e.g. only
  # "-" was specified)
  pass

#-----------------------------------------------------------------------------
# vim:ft=python
