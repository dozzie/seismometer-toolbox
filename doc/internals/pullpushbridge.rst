**********************
*pull-push-bridge* API
**********************

Architecture
============

Operation of *pull-push-bridge* is dumb-easy: it reads messages from a Streem
channel and sends them through output plugin instance (see
:ref:`pullpushbridge-api`). There will be only one instance of output plugin
throughout the life of *pull-push-bridge*.

By default, plugin is loaded from :mod:`seismometer.pull_push_bridge` package,
but can be specified as a path to Python file.

.. _pullpushbridge-api:

Plugin API
==========

.. class:: PullPushBridge

   .. attribute:: options

      :type: list of :class:`optparse.Option`

      A list of option instances created with :func:`optparse.make_option`
      function. These will be accepted as plugin-specific options from command
      line. Two options are reserved: ``--source`` with ``"source"``
      destination and ``--plugin`` with ``"plugin"`` destination.

      The field should be omitted if no options are to be added.

   .. method:: __init__(options)

      :param options: option object

      Option object keeps options as object's properties, as they were
      specified in :data:`options` field.

   .. method:: send(message)

      :param message: message received from Streem
      :type message: :class:`seismometer.message.Message`

      This method should consume the message, either by ignoring it or passing
      to appropriate service.
