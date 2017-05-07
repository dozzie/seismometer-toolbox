***********
*hailerter*
***********

Synopsis
========

.. code-block:: none

   hailerter [--socket=<path>] [options]
   hailerter --socket=<path> list
   hailerter --socket=<path> forget <aspect> <location>
   hailerter --socket=<path> list-muted
   hailerter --socket=<path> mute <aspect> <location> <duration>
   hailerter --socket=<path> unmute <aspect> <location>
   hailerter --socket=<path> reset-flapping <aspect> <location>
   hailerter --socket=<path> reset-reminder <aspect> <location>

Description
===========

*hailerter* is a state tracker for things monitored by Seismometer.
*hailerter* produces a message whenever a monitored object changes its status,
which usually is a much rarer event than probing the object's state, thus it's
easier to spot problems and react to them.

*hailerter* reads Seismometer messages from *STDIN*, one JSON per line, and
writes resulting events to *STDOUT*, again, one JSON per line. This can be
leveraged by using *hailerter* in combination with :manpage:`dumb-probe(8)` as
data source.

*hailerter* organizes monitored things into streams of status information,
identifying the streams with *aspect name* and *location* from Seismometer
message. Each stream is remembered and treated separately.

Options
=======

.. program:: hailerter

.. option:: --socket <path>

   Unix socket path to listen for control commands.

.. option:: --skip-initial-error

   Flag to prevent sending a notification for the first state about
   a previously unseen status stream, even if it's an error state.

   Default is to send a notification for the first state if it's an error.

.. option:: --remind-interval <interval>

   Interval between reminder messages that signal that status stream is still
   reporting an error, stream is still missing, or is still flapping.

   Default is not to send any reminders.

.. option:: --warning-expected

   Treat a state of severity ``"warning"`` as ``"expected"`` instead of
   ``"error"``.

.. option:: --default-interval <interval>

   Status collection interval to assume for a stream if an incoming message
   doesn't carry one.

.. option:: --missing <count>

   Number of messages from a status stream that didn't arrive before assuming
   that the stream is missing.

   Note that the count of 1 is probably a bad idea, as the collection and
   transporting system introduces some delay between an agent that is message
   source and *hailerter*.

   Default is not to watch for missing messages.

.. option:: --flapping-window <count>

   Number of messages to watch for status change for flapping detection.

   Both :option:`--flapping-window` and :option:`--flapping-threshold` need to
   be provided for flapping detection to be enabled.

.. option:: --flapping-threshold <fraction>

   Fraction of the watched messages (between ``0.0`` and ``1.0``) that need to
   change status to consider the status stream to be flapping.

   Both :option:`--flapping-window` and :option:`--flapping-threshold` need to
   be provided for flapping detection to be enabled.

Control commands
================

Since some streams that *hailerter* started tracking could disappear in
a planned and permanent way, *hailerter* provides a control interface for
managing the streams.

Control interface needs to be enabled by providing :option:`--socket` option.
This creates a unix stream socket with a simple request-reply protocol on
top. Requests and replies are JSON hashes, each encoded in a single line.
Connection is closed immediately after sending a reply.

Commands that *hailerter* supports can be sent by calling ``hailerter``
command, but the protocol description provided here is equally important.

Supported commands are following:

.. describe:: hailerter list

   List known monitored objects (aspect + location).

   * request: ``{"command":"list"}``
   * response: ``{"result":[<stream1>, <stream2>, ...]}``, where
     ``<streamX>`` is a hash structure ``{"aspect":"...",
     "location":{...}, "info":<info>}``, and ``<info>`` has the same
     structure as in :ref:`output format <hailerter-output>`

.. describe:: hailerter forget <aspect> <location>

   Delete all information about stream identified by ``<aspect>`` and
   ``<location>``.

   * request: ``{"command":"forget", "aspect":"...", "location":{...}}``

   * response: ``{"result":"ok"}``

.. describe:: hailerter list-muted

   List streams with suppressed notifications.

   * request: ``{"command":"list_muted"}``
   * response: ``{"result":[<stream1>, <stream2>, ...]}``, where
     ``<streamX>`` is a hash structure ``{"aspect":"...",
     "location":{...}, "expires":1234567890}``, with ``1234567890`` being unix
     timestamp when suppression expires

.. describe:: hailerter mute <aspect> <location> <duration>

   Suppress notifications about stream identified by ``<aspect>`` and
   ``<location>`` for specified duration. Suppressing a stream in advance,
   before *hailerter* learns about it, is a supported operation.

   ``<duration>`` has the same format as intervals.

   * request: ``{"command":"mute", "aspect":"...", "location":{...},
     "duration":<time>}``, where ``<time>`` is positive number of seconds

   * response: ``{"result":"ok"}``

.. describe:: hailerter unmute <aspect> <location>

   Re-enable notifications for stream identified by ``<aspect>`` and
   ``<location>``.

   * request: ``{"command":"unmute", "aspect":"...", "location":{...}}``

   * response: ``{"result":"ok"}``

.. describe:: hailerter reset-flapping <aspect> <location>

   Reset flapping counter for the stream identified by ``<aspect>`` and
   ``<location>``.

   Note that this command does not change stream's state nor triggers any
   notifications. State change will be only visible after next message in the
   stream.

   * request: ``{"command":"reset_flapping", "aspect":"...", "location":{...}}``

   * response: ``{"result":"ok"}``

.. describe:: hailerter reset-reminder <aspect> <location>

   Reset reminder interval for the stream identified by ``<aspect>`` and
   ``<location>``. Next message to come will trigger a reminder notification.

   * request: ``{"command":"reset_reminder", "aspect":"...", "location":{...}}``

   * response: ``{"result":"ok"}``

In the commands described above, ``<aspect>`` is a raw string not encoded in
any way, and ``<location>`` is a JSON string.

Input format
============

*hailerter* expects JSON messages on its *STDIN*, one per line. Any message
that is not a Seismometer message is discarded. If the message conforms to the
Seismometer structure, but only carries metrics, it's discarded as well.

.. _hailerter-output:

Output format
=============

*hailerter* prints notification messages on its *STDOUT*, one JSON hash per
line.

Some values in notification message are taken directly from Seismometer
message, so they follow their restrictions and format.

Notification message looks like this:

.. code-block:: none

   {"time": 1234567890, "aspect": "...", "location": { ... },
     "info": <info>, "previous": <info> | null}

``aspect`` (``event.name`` from Seismometer message) and ``location`` are
copied from the original message without change (thus ``aspect`` is a string,
and ``location`` is a hash with values being strings).

``info`` and ``previous`` fields carry the same data structure, which
describes current or past status of the monitored object. ``previous`` field
will be ``null`` if the notification concerns a stream never previously seen.
Obviously, a reminder message will have the same value in fields
``info.status`` and ``previous.status``.

``<info>`` structure describes one of the four statuses: OK (usually
a recovery), error (state degradation), flapping (status constantly changing,
and thus notifications being suppressed), or missing (state messages weren't
seen for a long time).

The structure itself
looks like this:

* ``{"status": "ok", "state": <state>, "severity": <severity>}``

  * ``<state>`` is a string, as in ``event.state.value``
  * ``<severity>`` is ``"expected"`` or ``"warning"``, as in
    ``event.state.severity``

* ``{"status": "degraded", "state": <state>, "severity": <severity>}``

  * ``<state>`` is a string, as in ``event.state.value``
  * ``<severity>`` is ``"warning"`` or ``"error"``, as in
    ``event.state.severity``

* ``{"status": "flapping", "window": <count>, "changes": <count>}``

  * ``<count>`` is a positive integer

* ``{"status": "missing", "last_seen": <timestamp>}``

  * ``<timestamp>`` is unix timestamp of the last message from the stream

Signals
=======

*SIGHUP*, *SIGINT*, and *SIGTERM* cause *hailerter* to terminate.

See Also
========

.. only:: man

   * message schema v3 <http://seismometer.net/message-schema/v3/>
   * :manpage:`seismometer-message(7)`
   * :manpage:`dumb-probe(8)`

.. only:: html

   * message schema v3 <http://seismometer.net/message-schema/v3/>
   * :doc:`dumbprobe`

