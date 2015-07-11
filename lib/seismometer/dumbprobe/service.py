#!/usr/bin/python
'''
Container for checks to be run by DumbProbe.

.. autoclass:: Queue
   :members:

.. autoclass:: Checks
   :members:

'''
#-----------------------------------------------------------------------------

import shell_command
import heapq
import time

#-----------------------------------------------------------------------------

class Queue:
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

    :obj:`command` is the same object as it was passed to :meth:`add`.
    '''
    (time, command) = heapq.heappop(self.queue)
    return (time, command)

#-----------------------------------------------------------------------------

class Checks:
  '''
  Container for checks to be executed.
  '''

  def __init__(self):
    self._checks = {}   # (host,service,aspect) -> *Plugin
    self._schedule = {} # (host,service,
    self._q = Queue()

  # type = "nagios" | "value" | "exit_code"
  def add(self, command, host, service, aspect, schedule,
          warning = None, critical = None, type = "nagios"):
    '''
    :param command: shell command to execute as a check
    :type command: string or array
    :param host: name of host running the monitored service
    :type host: string
    :param service: name of monitored service
    :type service: string
    :param aspect: name of monitored aspect
    :type aspect: string
    :param schedule: interval between consequent runs
    :type schedule: number of seconds
    :param warning: ignored for now
    :param critical: ignored for now
    :param type: type of command to run
    :type type: ``"nagios"``, ``"value"`` or ``"exit_code"``

    Types ``"value"`` and ``"exit_code"`` are not implemented yet.
    '''
    location = {'host': host, 'service': service}
    if type == "nagios":
      check = shell_command.NagiosPlugin(
        location = location, aspect = aspect,
        command = command, schedule = schedule,
        thresholds = (warning, critical)
      )
    elif type == "value":
      raise NotImplementedError("command printing value not implemented")
    elif type == "exit_code":
      raise NotImplementedError("command returning exit_code not implemented")
    else:
      raise ValueError("command printing value not implemented")

    self._checks[(host, service, aspect)] = check
    self._q.add(check.when(), check)

  def run_next(self):
    '''
    :return: dictionary representing :doc:`/api/message`

    Sleep until next check is expected to be run and run the check.
    '''
    (when, check) = self._q.get()
    self.sleep_until(when)
    result = check.run()
    self._q.add(check.when(), check)
    return result

  def sleep_until(self, when):
    '''
    :param when: Epoch timestamp to sleep until

    Sleep until it is the specified time.

    Method works fine when the time to sleep until is in the past.
    '''
    now = time.time()
    if now < when:
      time.sleep(when - now)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
