#!/usr/bin/python

import sys
import optparse
import seismometer.messenger
import yaml
import logging
import seismometer.logging
import signal

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
           " Seismometer Message",
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
    "--logging", dest = "logging_config",
    default = None,
    help = "YAML/JSON file with logging configuration",
    metavar = "FILE",
)

# }}}
#-----------------------------------------------------------------------------

(options, args) = parser.parse_args()

if len(args) > 0:
    parser.error("too many arguments")

if len(options.source) == 0:
    options.source = ["stdin"]

if len(options.destination) == 0:
    options.destination = ["stdout"]

#-----------------------------------------------------------------------------
# configure logging {{{

if options.logging_config is not None:
    cf = open(options.logging_config)
    seismometer.logging.dictConfig(yaml.safe_load(cf))
else:
    seismometer.logging.dictConfig({
        "version": 1,
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
        "formatters": {
            "brief_formatter": {
                "format": "[%(name)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief_formatter",
                "stream": "ext://sys.stderr",
            },
        },
    })

logger = logging.getLogger()

# }}}
#-----------------------------------------------------------------------------
# --source options parsing {{{

def prepare_source(source):
    if source == "stdin":
        logger.info("adding source: STDIN")
        import seismometer.messenger.net_input.stdin
        return seismometer.messenger.net_input.stdin.STDIN()

    if source.startswith("tcp:"):
        if ":" in source[4:]:
            (host, port) = source[4:].split(":")
            port = int(port)
            logger.info("adding source: TCP:*:%d", port)
        else:
            host = None
            port = int(source[4:])
            logger.info("adding source: TCP:%s:%d", host, port)
        import seismometer.messenger.net_input.inet
        return seismometer.messenger.net_input.inet.TCP(host, port)

    if source.startswith("udp:"):
        if ":" in source[4:]:
            (host, port) = source[4:].split(":")
            port = int(port)
            logger.info("adding source: UDP:*:%d", port)
        else:
            host = None
            port = int(source[4:])
            logger.info("adding source: UDP:%s:%d", host, port)
        import seismometer.messenger.net_input.inet
        return seismometer.messenger.net_input.inet.UDP(host, port)

    if source.startswith("unix:"):
        path = source[5:]
        logger.info("adding source: UNIX:%s", path)
        import seismometer.messenger.net_input.unix
        return seismometer.messenger.net_input.unix.UNIX(path)

    import json
    params = json.loads(source)
    import seismometer.messenger.net_input.plugin
    # TODO: log this
    # TODO: document this
    return seismometer.messenger.net_input.plugin.Plugin(params['class'],
                                                         params)

# }}}
#-----------------------------------------------------------------------------
# --destination options parsing {{{

def prepare_destination(destination):
    if destination == "stdout":
        logger.info("adding destination: STDOUT")
        import seismometer.messenger.net_output.stdout
        return seismometer.messenger.net_output.stdout.STDOUT()

    if destination.startswith("tcp:"):
        (host, port) = destination[4:].split(":")
        port = int(port)
        logger.info("adding destination: TCP:%s:%d", host, port)
        import seismometer.messenger.net_output.inet
        return seismometer.messenger.net_output.inet.TCP(host, port)

    if destination.startswith("udp:"):
        (host, port) = destination[4:].split(":")
        port = int(port)
        logger.info("adding destination: UDP:%s:%d", host, port)
        import seismometer.messenger.net_output.inet
        return seismometer.messenger.net_output.inet.UDP(host, port)

    if destination.startswith("unix:"):
        path = destination[5:]
        logger.info("adding destination: UNIX:%s", path)
        import seismometer.messenger.net_output.unix
        return seismometer.messenger.net_output.unix.UNIX(path)

    import json
    params = json.loads(destination)
    import seismometer.messenger.net_output.plugin
    # TODO: log this
    # TODO: document this
    return seismometer.messenger.net_output.plugin.Plugin(params['class'],
                                                          params)

# }}}
#-----------------------------------------------------------------------------

sources      = [prepare_source(o)      for o in options.source]
destinations = [prepare_destination(o) for o in options.destination]

tag_matcher = seismometer.messenger.tags.TagMatcher(options.tag_file)
reader = seismometer.messenger.net_input.Reader(tag_matcher)
writer = seismometer.messenger.net_output.Writer()

for s in sources:
    reader.add(s)
for d in destinations:
    writer.add(d)

#-----------------------------------------------------------------------------

# TODO:
#   * SIGUSR1: reload logging config
#   * SIGPIPE: SIG_IGN (when can it break things and how?)

def reload_tags(sig, stack_frame):
    logger = logging.getLogger("config")
    try:
        logger.info("reloading tag matcher")
        tag_matcher.reload()
    except Exception, e:
        logger.warn("tag matcher reload problem: %s", str(e))

def quit_daemon(sig, stack_frame):
    logger.info("received signal; shutting down")
    sys.exit(0)

signal.signal(signal.SIGHUP, reload_tags)
signal.signal(signal.SIGTERM, quit_daemon)

#-----------------------------------------------------------------------------
# main loop

try:
    while True:
        message = reader.read()
        writer.write(message)
except KeyboardInterrupt:
    logger.info("received signal; shutting down")
    pass
except seismometer.messenger.net_input.EOF:
    # this is somewhat expected: all the input descriptors are closed (e.g.
    # only STDIN was specified)
    pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
