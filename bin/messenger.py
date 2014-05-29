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

# TODO: verify `args'

#-----------------------------------------------------------------------------

# TODO:
#   * signal handlers:
#     * SIGPIPE: SIG_IGN
#     * SIGHUP: reload tag patterns
#     * SIGUSR1: reload logging config
#   * fsync'd STDOUT (use in pipe)
#   * date +"foo.bar $VALUE %s" | messenger.py -

#-----------------------------------------------------------------------------
# main loop

try:
  pass # TODO
except KeyboardInterrupt:
  pass

#-----------------------------------------------------------------------------
# vim:ft=python
