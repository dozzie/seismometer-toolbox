******************
*pull-push-bridge*
******************

*pull-push-bridge* is a generic forwarder of Streem messages. It's used for
passing stream of monitoring messages from one channel to external service or
to a different channel with some filtering and processing.

Usage
=====

Command line options
--------------------

.. cmdoption:: --destination <address>

   Destination for plugin. Depends on type of plugin (see :ref:`plugins`).

.. _plugins:

Plugins
=======

.. automodule:: panopticon.pull_push_bridge.collectd

.. automodule:: panopticon.pull_push_bridge.state_forwarder

.. automodule:: panopticon.pull_push_bridge.stdout

.. automodule:: panopticon.pull_push_bridge.webasdb

Plugin API
==========

.. class:: PullPushBridge(options)

   .. method:: send(message)
