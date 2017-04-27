***********
*hailerter*
***********

Synopsis
========

.. code-block:: none

   hailerter [options]

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

Input format
============

*hailerter* expects JSON messages on its *STDIN*, one per line. Any message
that is not a Seismometer message is discarded. If the message conforms to the
Seismometer structure, but only carries metrics, it's discarded as well.

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

