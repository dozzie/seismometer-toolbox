**********************
*pull-push-bridge* API
**********************

Architecture
============

Operation of *pull-push-bridge* is dumb-easy: it reads messages from a Streem
channel and sends them through output plugin instance (see
:ref:`pullpushbridge-api`). There will be only one instance of output plugin
throughout the life of *pull-push-bridge*.

Currently plugin is loaded from :mod:`panopticon.pull_push_bridge` module.

.. _pullpushbridge-api:

Plugin API
==========

.. class:: PullPushBridge

   .. method:: __init__(options)

      :param options: option object

      Option object keeps options as object's properties. The main option
      present is ``options.destination``.

   .. method:: send(message)

      :param message: message received from Streem
      :type message: :class:`panopticon.message.Message`

      This method should consume the message, either by ignoring it or passing
      to appropriate service.
