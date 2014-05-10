#!/usr/bin/python
#
# s = streem.Streem(...)
# s.register("probes")
#
# checks = Checks()
# for x in ...:
#   checks.add(...)
#
# while True:
#   msg = checks.run_next()
#   s.submit(msg)
#
#-----------------------------------------------------------------------------

import shell_command
import heapq
import time

#-----------------------------------------------------------------------------

class Queue:
  def __init__(self, elements = []):
    # elements = [(time, command), ...]
    self.queue = elements[:] # XXX: shallow copy of array
    heapq.heapify(self.queue)

  def empty(self):
    return len(self.queue) == 0

  def add(self, time, command):
    heapq.heappush(self.queue, (time, command))

  def get(self):
    (time, command) = heapq.heappop(self.queue)
    return (time, command)

#-----------------------------------------------------------------------------

class Checks:
  def __init__(self):
    self._checks = {}   # (host,service,aspect) -> *Plugin
    self._schedule = {} # (host,service,
    self._q = Queue()

  # type = "nagios" | "value" | "exit_code"
  def add(self, command, host, service, aspect, schedule,
          warning = None, critical = None, type = "nagios"):
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
    (when, check) = self._q.get()
    self.sleep_until(when)
    result = check.run()
    self._q.add(check.when(), check)
    return result

  def sleep_until(self, when):
    now = time.time()
    if now < when:
      time.sleep(when - now)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
