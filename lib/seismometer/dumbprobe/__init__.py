#!/usr/bin/python
'''
Available check classes
-----------------------

The classes that work with external commands (e.g. :class:`ShellOutputJSON` or
:class:`Nagios`) assume that if the command is specified as simple string, it
should be run with shell (``/bin/sh -c ...``), and if it's specified as
a list, it is run without invoking :file:`/bin/sh`. The latter is especially
important when the command is provided with calculated arguments.

.. autoclass:: BaseCheck
   :members:

.. autoclass:: Function
   :members:

.. autoclass:: ShellOutputJSON
   :members:

.. autoclass:: ShellOutputMetric
   :members:

.. autoclass:: ShellOutputState
   :members:

.. autoclass:: ShellExitState
   :members:

.. autoclass:: Nagios
   :members:

Available handle classes
------------------------

These classes are for receiving check results from external sources,
especially from command line tools that write status information in regular
intervals and don't exit on their own (a good example is ``vmstat 60``, which
prints OS statistics every 60 seconds).

.. autoclass:: BaseHandle
   :members:

.. autoclass:: ShellStream
   :members:

.. autoexception:: HandleEOF
   :members:

DumbProbe config interface
--------------------------

This interface is intended for use in script specified with :option:`--checks`
option, may also be useful as a basis for custom implementation.

.. autoclass:: Checks
   :members:

.. autoclass:: RunQueue
   :members:

'''
#-----------------------------------------------------------------------------

import heapq
import time
import logging
import seismometer.poll
import signal

from checks import *
from handles import *
__all__ = [
    'Checks',
    # XXX: all the classes from `checks' module
    'BaseCheck',
    'ShellOutputJSON', 'ShellOutputMetric', 'ShellOutputState',
    'ShellExitState', 'Nagios',
    'Function',
    # XXX: all the classes from `handles' module
    'BaseHandle', 'HandleEOF',
    'ShellStream',
]

#-----------------------------------------------------------------------------
# RunQueue {{{

class RunQueue:
    '''
    Queue for running commands at specified times.
    '''
    def __init__(self, elements = []):
        # elements = [(time, command), ...]
        self.queue = elements[:] # XXX: shallow copy of array
        heapq.heapify(self.queue)

    def __len__(self):
        '''
        :rtype: integer

        Return the size of the queue.
        '''
        return len(self.queue)

    def empty(self):
        '''
        :rtype: Boolean

        Check if the queue is empty.
        '''
        return len(self.queue) == 0

    def add(self, time, command):
        '''
        :param time: Epoch timestamp to run command at
        :param command: command to run

        Add a command to run at specified time.

        :obj:`command` is opaque to the queue.
        '''
        heapq.heappush(self.queue, (time, command))

    def get(self):
        '''
        :rtype: tuple (time, command)

        Return command that has earliest run time.

        :obj:`command` is the same object as it was passed to :meth:`add()`.
        '''
        (time, command) = heapq.heappop(self.queue)
        return (time, command)

    def peek(self):
        '''
        :rtype: tuple (time, command)

        Return command that has earliest run time without removing it from the
        queue.

        :obj:`command` is the same object as it was passed to :meth:`add()`.
        '''
        (time, command) = self.queue[0]
        return (time, command)

# }}}
#-----------------------------------------------------------------------------
# Alarm {{{

class Alarm:
    '''
    :manpage:`alarm(2)`-based notifier.
    '''

    def __init__(self):
        self.alarm_fired = False
        self.alarm_set = False

    def install_handler(self):
        '''
        Install :signal:`SIGALRM` handler of this object.
        '''
        signal.signal(signal.SIGALRM, self.handle_alarm)

    def reset_alarm(self):
        '''
        Reset alarm's state, cancelling any schedule.
        '''
        self.alarm_fired = False
        self.alarm_set = False
        signal.alarm(0)

    def set_alarm(self, when):
        '''
        :param when: timestamp to fire alarm on

        Set an alarm to be fired. If :obj:`when` is in the past, the alarm is
        considered to be fired already.
        '''
        when = int(when)
        now = int(time.time())
        if now < when:
            self.alarm_fired = False
            self.alarm_set = True
            signal.alarm(when - now)
        else:
            self.alarm_fired = True
            self.alarm_set = False

    def handle_alarm(self, sig, stack_trace):
        '''
        :signal:`SIGALRM` handler.
        '''
        self.alarm_fired = True
        self.alarm_set = False

    def is_set(self):
        '''
        :rtype: bool

        Check whether the alarm was set. Alarm that fired is unset.
        '''
        return self.alarm_set

    def fired(self):
        '''
        :rtype: bool

        Check whether the alarm has fired or not.
        '''
        return self.alarm_fired

# }}}
#-----------------------------------------------------------------------------

class Checks:
    '''
    Container for checks to be executed.
    '''

    def __init__(self, checks = None):
        self.q = RunQueue()
        self.poll = seismometer.poll.Poll()
        self.start_handles = []
        self.alarm = Alarm()
        self.alarm.install_handler()
        self.check_ids = {}
        if checks is not None:
            for c in checks:
                self.add(c)

    def check_name(self, check):
        '''
        :param check: a check or a handle
        :rtype: (integer, string)
        :return: check's index and name

        Return check's identity for logging.
        '''
        check_id = self.check_ids[id(check)]
        if hasattr(check, "check_name"):
            check_name = check.check_name()
        else:
            check_name = "C-%08X/%s.%s" % (
                id(check),
                check.__class__.__module__,
                check.__class__.__name__,
            )

        return (check_id, check_name)

    def add(self, check):
        '''
        :param check: check to run (typically an instance of
            :class:`BaseCheck` subclass)

        Add an entry to the list of checks to be run periodically.
        '''
        # XXX: since there's no `delete()' operation and the queue can only
        # grow at this point, length of the queue before adding the check is
        # the position of the check in the incoming list
        self.check_ids[id(check)] = len(self.q)
        (check_id, check_name) = self.check_name(check)

        logger = logging.getLogger("checks_queue")

        if isinstance(check, BaseHandle):
            self.start_handles.append(check)
            return

        # it's a regular check with a schedule

        next_run = check.next_run()
        if next_run < time.time():
            logger.info("adding check #%d %s to run now", check_id, check_name)
        else:
            logger.info("adding check #%d %s to run at @%d",
                        check_id, check_name, next_run)
        self.q.add(next_run, check)

    def setup_handles(self):
        '''
        Open all added handles.
        '''
        logger = logging.getLogger("checks_queue")
        for handle in self.start_handles:
            (check_id, check_name) = self.check_name(handle)

            try:
                handle.open()
            except Exception, e:
                # schedule a reopen
                reopen_time = int(time.time()) + 60 # FIXME: hardcoded
                logger.warn("handle #%d %s start failed: %s; reopening at @%d",
                            check_id, check_name, str(e), reopen_time)
                self.q.add(reopen_time, handle)
                continue

            logger.info("adding handle #%d %s to poll queue",
                        check_id, check_name)
            self.poll.add(handle)
        del self.start_handles[:]

    def run_next(self):
        '''
        :return: non-empty list of dicts and
            :class:`seismometer.message.Message` instances

        Sleep until next check is expected to be run and run the check, or
        read messages from polled handles, if any are available.
        '''
        result = None
        while result is None:
            result = self._run_next_once()
        return result

    def _run_next_once(self):
        '''
        :return: list of dicts and :class:`seismometer.message.Message`
            instances, or ``None`` if no messages were read

        Sleep until next check is expected to be run and run the check, or
        read messages from polled handles, if any are available.

        Function may return ``None`` when some handles needed maintenance
        (closing or reopening), or when a check returned ``None`` or empty
        list of messages.
        '''
        read_handles = self.poll_handles()

        if read_handles is not None:
            result = self.read_handles(read_handles)
            if len(result) == 0:
                return None
            return result

        # no handles to read, so poll() must have been interrupted with
        # SIGALRM or the check was already due

        if self.q.empty():
            return None

        (next_run, check) = self.q.peek()
        if int(next_run) > int(time.time()):
            # this could be SIGALRM sent to the DumbProbe manually, or maybe
            # some other scenario I haven't thought about
            return None
        self.q.get() # remove the check from the queue

        if isinstance(check, BaseHandle):
            # this wasn't a check, but a handle that needs being reopened
            self.reopen_handle(check)
            return None

        # XXX: `check' is a check object, possibly BaseCheck instance, but not
        # necessarily
        result = self.run_check(check)
        self.q.add(int(check.next_run()), check)

        if isinstance(result, (list, tuple)) and len(result) == 0:
            return None
        elif isinstance(result, tuple):
            return list(result)
        elif isinstance(result, list):
            return result
        else: # dict or seismometer.message.Message
            return [result]

    def poll_handles(self):
        '''
        :return: list of :class:`BaseHandle` or ``None``

        Poll the watched handles for input and return a list of the ones ready
        for reading. If the time for running next check from the schedule has
        come, ``None`` is returned.
        '''
        if not self.q.empty():
            (next_run, check) = self.q.peek()
            if int(next_run) <= int(time.time()):
                self.alarm.reset_alarm()
                return None

            if not self.alarm.is_set():
                self.alarm.set_alarm(next_run)

        handles = self.poll.poll(timeout = None)
        if len(handles) == 0:
            # poll() was interrupted, most probably by SIGALRM
            return None
        return handles

    def read_handles(self, handles):
        '''
        :param handles: list of :class:`BaseHandle` objects to read
        :return: list (possibly empty) of dicts and
            :class:`seismometer.message.Message` instances

        Read all messages from passed handles and return them as a single,
        flat list.

        Handles that encountered EOF are closed (:meth:`BaseHandle.close()`),
        removed from poll queue, and scheduled for reopen
        (:meth:`BaseHandle.open()`).
        '''
        logger = logging.getLogger("checks_queue")

        result = []
        for handle in handles:
            (check_id, check_name) = self.check_name(handle)
            try:
                result.extend(handle.read_messages())
            except HandleEOF, e:
                # EOF; remove from polling and schedule reopen
                reopen_time = int(time.time()) + 60 # FIXME: hardcoded
                logger.warn("handle #%d %s returned EOF: %s; reopening at @%d",
                            check_id, check_name, str(e), reopen_time)
                self.poll.remove(handle)
                handle.close()
                self.q.add(reopen_time, handle)
            except Exception, e:
                # probably a processing error; log the message and continue
                logger.warn("handle #%d %s raised a read exception: %s",
                            check_id, check_name, str(e))

        return result

    def reopen_handle(self, handle):
        '''
        :param handle: :class:`BaseHandle` to be reopened

        Reopen a handle and add it to poll list. If reopen fails, the handle
        is scheduled for another one.
        '''
        logger = logging.getLogger("checks_queue")
        (check_id, check_name) = self.check_name(handle)

        try:
            handle.open()
        except Exception, e:
            # schedule next reopen
            reopen_time = int(time.time()) + 60 # FIXME: hardcoded
            logger.warn("handle #%d %s reopen failed: %s; reopening at @%d",
                        check_id, check_name, str(e), reopen_time)
            self.q.add(reopen_time, handle)
            return
        self.poll.add(handle)
        logger.info("handle #%d %s reopened", check_id, check_name)

    def run_check(self, check):
        '''
        :param check: check (:class:`BaseCheck` or compatible) to be run
        :return: list or tuple of messages, a single message (dict or
            :class:`seismometer.message.Message`), or ``None``

        Run a check and return its result. If the check raised an exception,
        the exception is logged and ``None`` is returned.
        '''
        logger = logging.getLogger("checks_queue")
        (check_id, check_name) = self.check_name(check)
        result = None
        try:
            result = check.run()
        except Exception, e:
            logger.warn("check #%d %s raised exception: %s",
                        check_id, check_name, str(e))
            return None

        if result is None:
            # a check is not really expected to return `None', because it may
            # mean that a "return" was forgotten somewhere; if a check needs
            # to return "no results", then it may return an empty list/tuple
            logger.info("check #%d %s has returned nothing",
                        check_id, check_name)
        return result

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
