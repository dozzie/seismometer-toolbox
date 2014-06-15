#!/usr/bin/python
#
# Bridge between Streem and passive services that collect monitoring data,
# like Graphite or collectd.
#
# The bridge pulls messages from Streem and pushes them to specified service.
#
#-----------------------------------------------------------------------------

import sys
import optparse
import streem
import imp
import panopticon.message
import panopticon.plugin
import panopticon.pull_push_bridge

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
  "--destination", dest = "destination",
  help = "destination of messages with state (format depends on plugin)",
  metavar = "TARGET",
)
parser.add_option(
  "--plugin", dest = "plugin", default = "stdout",
  help = "plugin used to connect to destination (stdout is the default)",
  metavar = "PLUGIN",
)

(options, args) = parser.parse_args()

if options.source is None or options.destination is None:
  parser.print_help()
  sys.exit(1)

#-----------------------------------------------------------------------------
# main loop

(host, port, channel) = options.source.split(":", 2)
channel_in = streem.Streem(host, int(port))
channel_in.subscribe(channel)

ploader = panopticon.plugin.PluginLoader()
if options.plugin in panopticon.pull_push_bridge.PLUGINS:
  plugin = ploader.load('panopticon.pull_push_bridge.%s' % (options.plugin))
else:
  plugin = ploader.load('panopticon.pull_push_bridge._plugin', options.plugin)
ploader.close()

channel_out = plugin.PullPushBridge(options)

try:
  while True:
    m = channel_in.receive()
    try:
      msg = panopticon.message.Message(message = m)
    except ValueError:
      continue
    channel_out.send(msg)
except KeyboardInterrupt:
  pass

#-----------------------------------------------------------------------------
# vim:ft=python
