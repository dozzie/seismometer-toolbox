#!/usr/bin/python
'''
DumbProbe config interface
--------------------------

This interface is intended for use in script specified with :option:`--checks`
option.

.. autoclass:: Checks
   :members:

Available check classes
-----------------------

The classes that work with external commands (e.g. :class:`ShellOutputJSON` or
:class:`Nagios`) assume that if the command is specified as simple string, it
should be run with shell (``/bin/sh -c ...``), and if it's specified as
a list, it is run without invoking :file:`/bin/sh`. The latter is especially
important when the command is provided with calculated arguments.

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

.. autoclass:: Function
   :members:

.. autoclass:: BaseCheck
   :members:

'''
#-----------------------------------------------------------------------------

import heapq
import time

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

class Checks:
    '''
    Container for checks to be executed.
    '''

    def __init__(self, checks = None):
        self.q = Checks.RunQueue()
        if checks is not None:
            for c in checks:
                self.add(c)

    def add(self, check):
        self.q.add(check.next_run(), check)

    def run_next(self):
        '''
        :return: non-empty list of dicts and
            :class:`seismometer.message.Message` instances

        Sleep until next check is expected to be run and run the check.
        '''
        # loop until the first check encountered returns something meaningful
        result = None
        while result is None:
            (next_run, check) = self.q.get()
            self.sleep_until(next_run)
            try:
                result = check.run()
            finally:
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

    #-------------------------------------------------------
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
    #-------------------------------------------------------

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
