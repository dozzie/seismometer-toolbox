#!/usr/bin/python

import sys
import optparse
import time

from panopticon import daemonshepherd

#-----------------------------------------------------------------------------
# parse command line options {{{

# TODO: logging config

parser = optparse.OptionParser(
  usage = "%prog [options] --daemons=FILE",
)

parser.add_option(
  "-f", "--daemons", dest = "daemons",
  help = "YAML file with daemons to control", metavar = "FILE",
)
parser.add_option(
  "-s", "--control-socket", dest = "control_socket",
  help = "path or host:port to control socket", metavar = "FILE|ADDRESS",
)
parser.add_option(
  "-p", "--pid-file", dest = "pid_file",
  help = "PID file for going daemon", metavar = "FILE",
)
parser.add_option(
  "-d", "--background", dest = "background",
  action = "store_true", default = False,
  help = "detach from terminal (run as a daemon)",
)
parser.add_option(
  "-u", "--user", dest = "user",
  help = "user to run as",
)
parser.add_option(
  "-g", "--group", dest = "group",
  help = "group to run as",
)

(options, args) = parser.parse_args()

if options.daemons is None:
  parser.print_help()
  sys.exit(1)

# }}}
#-----------------------------------------------------------------------------

pid_file = None
controller = None

#-----------------------------------------------------------------------------
# create pidfile (if applicable) {{{

if options.pid_file is not None:
  pid_file = daemonshepherd.PidFile(options.pid_file)

# }}}
#-----------------------------------------------------------------------------
# change user/group (if applicable) {{{

if options.user is not None or options.group is not None:
  daemonshepherd.setguid(options.user, options.group)

# }}}
#-----------------------------------------------------------------------------
# daemonize (if applicable) {{{

if options.background:
  daemonshepherd.detach("/")
  pid_file.update()

pid_file.claim() # remove on close

# }}}
#-----------------------------------------------------------------------------
# create controller thread {{{

controller = daemonshepherd.Controller(options.daemons, self.control_socket)

# }}}
#-----------------------------------------------------------------------------
# acknowledge success to parent process (if --background) {{{

if options.background:
  daemonshepherd.detach_succeeded()

# }}}
#-----------------------------------------------------------------------------
# main loop {{{

try:
  while True:
    time.sleep(1)
except KeyboardInterrupt:
  pass

controller.shutdown()

# }}}
#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
