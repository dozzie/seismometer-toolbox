*******************
DumbProbe internals
*******************

Architecture
============

DumbProbe is centered around a module with checks to run. This module needs
to define ``CHECKS`` variable, which can be a list, tuple, or an object.

``CHECKS`` as an object
-----------------------

The only thing ``CHECKS`` object must have is a method called
:meth:`run_next()`. This method will be called with no arguments and is
supposed to wait until appropriate time comes and return an iterable with
messages to send to destination.

The messages can be :class:`seismometer.message.Message` or JSON-serializable
dictionary. Nothing more is expected of them.

``CHECKS`` as a list
--------------------

When ``CHECKS`` is a list (or tuple), a container
:class:`seismometer.dumbprobe.Checks` is created to schedule execution of
checks. This container provides :meth:`run_next()` method and does all the
work for DumbProbe.

The container recognizes two types of objects: handles to read from as soon as
any data arrives and checks to be called when their schedule comes.

A handle is a subclass of :class:`seismometer.dumbprobe.BaseHandle`. Its
:meth:`read_messages()` method is supposed to work in non-blocking manner.
When an end-of-file happens, the handle is closed and scheduled for reopen by
the checks container. Handle should start in a closed state and will be opened
by the call to :meth:`open()` method.

A check to be called is an object with following methods:

* :meth:`next_run()` should return time (unix timestamp) when the next
  execution should occur; checks container will run the check as soon as it
  can after that time
* :meth:`run()` is supposed to immediately execute the check and return its
  result (:class:`Message <seismometer.message.Message>` or dict) or
  list/tuple of the results

  * **NOTE**: ``None`` is not allowed here to prevent accidental omissions of
    ``return`` keyword; to signal that no message should be sent from this
    run, a check should return an empty list or tuple

* :meth:`check_name()` is an optional method that returns a string identifier
  for the check instance, which will be used in DumbProbe's logs; if not
  defined, the checks container will name the checks according to their Python
  class and position in the checks list (initial value of ``CHECKS``)

Checks to be called (and handles to be reopened) are stored in *run queue*,
along with the times when they should be called. After each execution the
checks are re-entered to the queue with new call time.
