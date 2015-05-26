#!/usr/bin/python

import sys
import optparse
import logging
import socket
import json

from seismometer import daemonshepherd
from seismometer.daemonshepherd.control_socket import ControlSocketClient

#-----------------------------------------------------------------------------
# parse command line options {{{

parser = optparse.OptionParser(
    usage = "\n  %prog [options] --daemons=FILE"
            "\n  %prog [options] reload"
            "\n  %prog [options] ps"
            "\n  %prog [options] {start|stop|restart|cancel_restart} <daemon_name>"
)

parser.add_option(
    "-f", "--daemons", dest = "daemons",
    help = "YAML file with daemons to control", metavar = "FILE",
)
parser.add_option(
    "-l", "--logging", dest = "logging",
    help = "YAML/JSON file with logging configuration", metavar = "FILE",
)
parser.add_option(
    "-s", "--control-socket", dest = "control_socket",
    default = "/var/run/daemonshepherd.sock",
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
# assume this until proven otherwise
command = "daemon_supervisor"

SOLE_COMMANDS = set(["reload", "ps"])
DAEMON_COMMANDS = set(["start", "stop", "restart", "cancel_restart"])
KNOWN_COMMANDS = SOLE_COMMANDS | DAEMON_COMMANDS

if len(args) == 0 and options.daemons is None:
    parser.error("--daemons option is required for this mode")
elif len(args) > 0:
    command = args.pop(0)
    if command not in KNOWN_COMMANDS:
        parser.error("unrecognized command: %s" % (command,))
    if len(args) != 1 and command in DAEMON_COMMANDS:
        parser.error("daemon name is required for command %s" % (command,))

# }}}
#-----------------------------------------------------------------------------

if command == "daemon_supervisor":
    #------------------------------------------------------
    # run as a daemon supervisor {{{

    pid_file = None
    controller = None

    # create pidfile (if applicable) 
    if options.pid_file is not None:
        pid_file = daemonshepherd.PidFile(options.pid_file)

    # change user/group (if applicable) 
    if options.user is not None or options.group is not None:
        daemonshepherd.setguid(options.user, options.group)

    # configure logging (if applicable) 
    if options.logging is not None:
        # JSON is valid YAML, so I can skip loading json module (yaml module
        # is necessary for daemons spec file anyway)
        import yaml
        log_config = yaml.safe_load(open(options.logging))
    else:
        log_config = {
            "version": 1,
            "root": { "handlers": ["null"] },
            "handlers": {
                "null": {
                    "class": "logging.StreamHandler",
                    "stream": open('/dev/null', 'w'),
                }
            }
        }

    import seismometer.logging
    seismometer.logging.dictConfig(log_config)

    # daemonize (if applicable) 
    if options.background:
        daemonshepherd.detach("/")
        if pid_file is not None:
            pid_file.update()

    if pid_file is not None:
        pid_file.claim() # remove on close

    # create controller thread 
    try:
        controller = daemonshepherd.Controller(options.daemons,
                                               options.control_socket)
    except Exception, e:
        print >>sys.stderr, str(e)
        sys.exit(1)

    # acknowledge success to parent process (if --background) 
    if options.background:
        daemonshepherd.detach_succeeded()

    # main loop 
    try:
        controller.loop()
    except KeyboardInterrupt:
        pass

    controller.shutdown()
    sys.exit()

    # }}}
    #------------------------------------------------------
else:
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        conn.connect(options.control_socket)
    except socket.error, e:
        print >>sys.stderr, e
        sys.exit(1)

    supervisor = ControlSocketClient(conn)

    if command in SOLE_COMMANDS:
        supervisor.send({"command": command})
    elif command in DAEMON_COMMANDS:
        supervisor.send({"command": command, "daemon": args[0]})
    reply = supervisor.read()
    supervisor.close()

    if reply.get("status") != "ok":
        print >>sys.stderr, json.dumps(reply)
        sys.exit(1)

    if command == "ps":
        for daemon in reply["result"]:
            print json.dumps(daemon)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
