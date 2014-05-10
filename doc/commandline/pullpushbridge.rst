******************
*pull-push-bridge*
******************

*pull-push-bridge* is a generic forwarder of Streem messages. It's used for
passing stream of monitoring messages from one channel to external service or
to a different channel with some filtering and processing.

Usage
=====

.. code-block:: none

   pull-push-bridge.py --source=<streem> --plugin=<plugin> --destination=<address>

Command line options
--------------------

.. cmdoption:: --source <host>:<port>:<channel>

   Streem address and channel to read messages from.

.. cmdoption:: --plugin <name>

   Name of plugin. See :ref:`plugins` for list of available plugins.

.. cmdoption:: --destination <address>

   Destination for plugin. Depends on type of plugin.

.. _plugins:

Plugins
=======

.. automodule:: panopticon.pull_push_bridge.collectd

.. automodule:: panopticon.pull_push_bridge.state_forwarder

.. automodule:: panopticon.pull_push_bridge.stdout

.. automodule:: panopticon.pull_push_bridge.webasdb

