#!/usr/bin/python
'''
DumbProbe config interface
--------------------------

This interface is intended for use in script specified with :option:`--checks`
option, may also be useful as a basis for custom implementation.

.. autoclass:: Checks
   :members:

.. autoclass:: RunQueue
   :members:

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

'''
#-----------------------------------------------------------------------------

import heapq
import time
import logging
import seismometer.poll
import signal

from checks import *
__all__ = [
    'Checks',
    # XXX: all the classes from `checks' module
    'BaseCheck',
    'ShellOutputJSON', 'ShellOutputMetric', 'ShellOutputState',
    'ShellExitState', 'Nagios',
    'Function',
]

#-----------------------------------------------------------------------------

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
        self.alarm = Alarm()
        self.alarm.install_handler()
        self.check_ids = {}
        if checks is not None:
            for c in checks:
                self.add(c)

    def check_name(self, check):
        '''
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
        logger = logging.getLogger("checks_queue")
        next_run = check.next_run()
        # XXX: since there's no `delete()' operation and the queue can only
        # grow at this point, length of the queue before adding the check is
        # the position of the check in the incoming list
        self.check_ids[id(check)] = len(self.q)
        (check_id, check_name) = self.check_name(check)
        if next_run < time.time():
            logger.info("adding check #%d %s to run now", check_id, check_name)
        else:
            logger.info("adding check #%d %s to run at @%d",
                        check_id, check_name, next_run)
        self.q.add(next_run, check)

    def run_next(self):
        '''
        :return: non-empty list of dicts and
            :class:`seismometer.message.Message` instances

        Sleep until next check is expected to be run and run the check.
        '''
        logger = logging.getLogger("checks_queue")
        # loop until the first check encountered returns something meaningful
        result = None
        while result is None:
            # XXX: if some messages were read from descriptors and returned
            # and the alarm has fired when the messages were being processed,
            # `next_run' will be a time in the past and alarm will immediately
            # report that it has fired
            (next_run, check) = self.q.peek()
            (check_id, check_name) = self.check_name(check)
            if not self.alarm.is_set():
                self.alarm.set_alarm(next_run)
                logger.info("sleeping %ds to run check #%d %s",
                            max(next_run - time.time(), 0),
                            check_id, check_name)

            while not self.alarm.fired():
                # TODO: read whatever came from the polled handles and return
                # it to the caller; for now it's just SIGALRM-safe sleep
                # NOTE: poll() is interrupted by SIGALRM
                self.poll.poll(timeout = None)

            # XXX: alarm has fired and nothing was read from polled
            # descriptors

            self.q.get() # drop the check, as it's now to be run

            try:
                result = check.run()
            except Exception, e:
                logger.warn("check #%d %s raised exception: %s",
                            check_id, check_name, str(e))
                self.q.add(check.next_run(), check)
                continue
            if result is None:
                logger.info("check #%d %s has returned nothing",
                            check_id, check_name)
            self.q.add(check.next_run(), check)
        if isinstance(result, list):
            return result
        elif isinstance(result, tuple):
            return list(result)
        else: # either seismometer.message.Message or dict
            return [result]

    def sleep_until(self, when):
        '''
        :param when: epoch timestamp of point to wake from sleep

        Sleep until it is the specified time.

        Method works fine when the time to sleep until is in the past.
        '''
        now = time.time()
        while now < when:
            # it may be interrupted by some ignored signal
            time.sleep(when - now)
            now = time.time()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
