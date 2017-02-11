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

# }}}
#-----------------------------------------------------------------------------

class Checks:
    '''
    Container for checks to be executed.
    '''

    def __init__(self, checks = None):
        self.q = RunQueue()
        if checks is not None:
            for c in checks:
                self.add(c)

    @staticmethod
    def check_id(check):
        return "C-%08X/%s.%s" % (
            id(check),
            check.__class__.__module__,
            check.__class__.__name__,
        )

    def add(self, check):
        '''
        :param check: check to run (typically an instance of
            :class:`BaseCheck` subclass)

        Add an entry to the list of checks to be run periodically.
        '''
        logger = logging.getLogger("checks_queue")
        next_run = check.next_run()
        if next_run < time.time():
            logger.info("adding check %s to run now", Checks.check_id(check))
        else:
            logger.info("adding check %s to run at @%d",
                        Checks.check_id(check), next_run)
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
            (next_run, check) = self.q.get()
            logger.info("sleeping %ds to run %s",
                        max(next_run - time.time(), 0), Checks.check_id(check))
            self.sleep_until(next_run)
            try:
                result = check.run()
            except Exception, e:
                logger.warn("%s raised exception: %s",
                            Checks.check_id(check), str(e))
                self.q.add(check.next_run(), check)
                continue
            if result is None:
                logger.info("%s has returned nothing", Checks.check_id(check))
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
