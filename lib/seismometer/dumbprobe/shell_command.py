#!/usr/bin/python
'''
Helper module for running external commands.

.. autoclass:: NagiosPlugin
   :members:

.. autoclass:: ShellCommand
   :members:

'''
#-----------------------------------------------------------------------------

import subprocess
import time
import re
from seismometer.message import Message

#-----------------------------------------------------------------------------

class NagiosPlugin:
  '''
  Nagios plugin executor.
  '''

  PERFDATA = re.compile(
    "(?P<label>[^ '=]+|'(?:[^']|'')*')=" \
    "(?P<value>[0-9.]+)"                 \
    "(?P<unit>[um]?s|%|[KMGT]?B|c)?"     \
      "(?:;(?P<warn>[0-9.]*)"            \
        "(?:;(?P<crit>[0-9.]*)"          \
          "(?:;(?P<min>[0-9.]*)"         \
            "(?:;(?P<max>[0-9.]*))?"     \
          ")?" \
        ")?" \
      ")?"
  )

  @staticmethod
  def perfdata(output):
    '''
    :param output: full output from plugin
    :type output: string

    Extract performance data from output collected from plugin.
    '''
    lines = output.split('\n')[0].split('|', 1)
    if len(lines) > 1:
      return lines[1].strip()
    else:
      return None

  @staticmethod
  def nagiosplugins(perfdata):
    '''
    :param perfdata: performance data portion from plugin's output
    :type perfdata: string
    :return: list of metrics
    :rtype: list of dicts or ``None``

    Extract metrics, value ranges and thresholds from performance data.

    Each metric is a dict with following keys:

       * *label* -- mandatory; string
       * *value* -- mandatory; integer, float or None
       * *min*, *max* -- optional; integer or float
       * *warn*, *crit* -- optional; integer or float

    Example returned data::

       [{"label": "uptime", "value": 17143.36, "min": 0}, ...]
    '''
    groups = []

    while perfdata != '' and perfdata is not None:
      match = NagiosPlugin.PERFDATA.match(perfdata)
      if match is None: # non-plugins-conforming perfdata, abort
        return None
      groups.append(match.groupdict())
      perfdata = perfdata[match.end():].lstrip()

    for group in groups:
      # nullify empty strings
      for key in group:
        if group[key] == '':
          group[key] = None
      # integerize integers, floatize floats
      for key in ['value', 'min', 'max', 'warn', 'crit']:
        if group[key] is not None:
          if '.' in group[key]: group[key] = float(group[key])
          else:                 group[key] = int(group[key])
      # strip label from single quotes, if apply
      if group['label'].startswith("'"):
        group['label'] = group['label'][1:-1].replace("''", "'")

    if len(groups) == 0:
      return None
    else:
      return groups

  def __init__(self, location, aspect, command, schedule, thresholds):
    '''
    :param location: location to report for this instance
    :type location: dict, mapping string => string
    :param aspect: aspect name to report for this instance
    :type aspect: string
    :param command: command to run
    :type command: string or array
    :param schedule: interval between consequent runs
    :type schedule: number of seconds
    :param thresholds: ignored for now
    :type thresholds: tuple (warning, critical)
    '''
    self.command = ShellCommand(command)
    self.location = location
    self.aspect   = aspect
    self.schedule = schedule
    self.thresholds = thresholds  # (warning, critical)
    self.last_run = 0

  def run(self):
    '''
    :return: dictionary representing :doc:`/message`

    Execute the plugin and return message to submit to Streem.
    '''
    codes = {
      0: ('ok', 'expected'),
      1: ('warning', 'warning'),
      2: ('critical', 'error'),
      #3: ('unknown', 'error'), # will be handled by codes.get()
    }

    (exit_code, output) = self.command.run()
    perfdata = NagiosPlugin.perfdata(output)
    data = NagiosPlugin.nagiosplugins(perfdata)
    (state, severity) = codes.get(exit_code, ('unknown', 'error'))

    self.last_run = time.time()

    has_thresholds = False

    event = Message(
      aspect = self.aspect,
      location = self.location,
      state = state,
      severity = severity,
      interval = self.schedule,
    )

    if data is not None:
      for datum in data:
        name = datum['label']
        event[name] = datum['value']

        if datum['warn'] is not None:
          event[name].set_above(datum['warn'], 'warning', 'warning')
          has_thresholds = True
        if datum['crit'] is not None:
          event[name].set_above(datum['crit'], 'critical', 'error')
          has_thresholds = True

        if datum['unit'] is not None:
          event[name].unit = datum['unit']

    # if there are values with thresholds, the status should reflect
    # thresholds being exceeded; if there's no thresholds (either because
    # they're not set for values or there are no values), state is to be
    # passed
    if has_thresholds:
      del event.state

    return event.to_dict()

  def when(self):
    '''
    Calculate when the plugin should be executed.
    '''
    return self.last_run + self.schedule

#-----------------------------------------------------------------------------

class ShellCommand:
  '''
  Wrapper class for running shell commands.
  '''
  def __init__(self, command):
    '''
    :param command: command to run
    :type command: string or list

    If :obj:`command` is a string, it will be run using shell (so it can be
    a shell script). A list will be run without shell.
    '''
    self.command = command

  def run(self):
    '''
    :return: exit code and command's output
    :rtype: tuple (integer, string)

    Execute the command.

    When exit code is negative, it denotes signal the command died on.
    '''
    if isinstance(self.command, list):
      proc = subprocess.Popen(
        self.command,
        stdin  = open("/dev/null"),
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
      )
    else:
      proc = subprocess.Popen(
        self.command, shell = True,
        stdin  = open("/dev/null"),
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
      )

    output = proc.stdout.read()
    # < 0  -- signal
    # >= 0 -- exit code
    exit_code = proc.wait()

    return (exit_code, output)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
