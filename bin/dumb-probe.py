#!/usr/bin/python

import sys
import optparse
import streem
import panopticon.plugin

#-----------------------------------------------------------------------------
# parse command line options

parser = optparse.OptionParser(
  usage = "%prog --checks=PYFILE [--destination=stdout | --destination=host:port:channel]",
)

parser.add_option(
  "--checks", dest = "checks",
  help = "load checks from *.py file", metavar = "PYFILE",
)
parser.add_option(
  "--destination", dest = "destination", default = "stdout",
  help = "where to submit messages to (host:port:channel or stdout;"
         " stdout is the default)",
  metavar = "TARGET",
)

(options, args) = parser.parse_args()

if options.checks is None:
  parser.print_help()
  sys.exit(1)

#-----------------------------------------------------------------------------
# prepare run environment: checks object and submit() function

ploader = panopticon.plugin.PluginLoader()
checks_mod = ploader.load('panopticon.dumbprobe.__config__', options.checks)
checks = checks_mod.checks
ploader.close()

if options.destination == "stdout":
  def submit(data):
    print data
else:
  (host, port, channel) = options.destination.split(":", 2)
  s = streem.Streem(host, int(port))
  s.register(channel)
  def submit(data):
    s.submit(data)

#-----------------------------------------------------------------------------
# main loop

try:
  while True:
    m = checks.run_next()
    submit(m)
except KeyboardInterrupt:
  pass

#-----------------------------------------------------------------------------
# vim:ft=python
