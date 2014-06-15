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

#-----------------------------------------------------------
# small helper for loading plugin's options

def load_plugin_opts(option, opt, value, parser):
  if parser.values.plugin is not None:
    raise optparse.OptionValueError("can't use two plugins")

  ploader = panopticon.plugin.PluginLoader()
  if value in panopticon.pull_push_bridge.PLUGINS:
    plugin = ploader.load("panopticon.pull_push_bridge.%s" % (value))
  else:
    plugin = ploader.load("panopticon.pull_push_bridge._plugin", value)
  ploader.close()

  parser.values.plugin = plugin
  if hasattr(plugin.PullPushBridge, "options"):
    optgroup = optparse.OptionGroup(parser, "Plugin-specific options")
    optgroup.add_options(plugin.PullPushBridge.options)
    parser.add_option_group(optgroup)

#-----------------------------------------------------------

parser = optparse.OptionParser(
  usage = "\n  %prog --source=SOURCE --plugin=PLUGIN [plugin options]" \
          "\n  %prog --plugin=PLUGIN --help"
)

parser.add_option(
  "--source", dest = "source",
  help = "source of messages with state (host:port:channel)",
  metavar = "SOURCE",
)
parser.add_option(
  "--plugin", dest = "plugin", type = "string",
  action = "callback", callback = load_plugin_opts, # will also set the value
  help = "plugin used to connect to destination (stdout is the default)",
  metavar = "PLUGIN",
)

(options, args) = parser.parse_args()

if options.source is None:
  parser.print_help()
  sys.exit(1)

if options.plugin is None:
  # plugin defaults to "stdout"
  import panopticon.pull_push_bridge.stdout
  options.plugin = panopticon.pull_push_bridge.stdout

#-----------------------------------------------------------------------------
# main loop

(host, port, channel) = options.source.split(":", 2)
channel_in = streem.Streem(host, int(port))
channel_in.subscribe(channel)

channel_out = options.plugin.PullPushBridge(options)

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
