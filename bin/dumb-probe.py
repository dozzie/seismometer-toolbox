#!/usr/bin/python

import sys
import optparse
import streem

#-----------------------------------------------------------------------------
# utility to load checks from specified file

def load_checks(filename):
  # hack for not write *.pyc file to the location of config file
  import imp, tempfile, os
  tmpdir = tempfile.mkdtemp()
  dummy_filename = os.path.join(tmpdir, 'config.py')
  plugin = imp.load_source('config', dummy_filename, open(filename))
  os.remove(dummy_filename + 'c')
  os.rmdir(tmpdir)
  return plugin.checks

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

checks = load_checks(options.checks)

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
