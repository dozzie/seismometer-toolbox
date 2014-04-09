#!/usr/bin/python

import subprocess
import time
import re

#-----------------------------------------------------------------------------

class NagiosPlugin:
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
    lines = output.split('\n')[0].split('|', 1)
    if len(lines) > 1:
      return lines[1].strip()
    else:
      return None

  @staticmethod
  def nagiosplugins(perfdata):
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
    self.command = ShellCommand(command)
    self.location = location
    self.aspect   = aspect
    self.schedule = schedule
    self.thresholds = thresholds  # (warning, critical)
    self.last_run = 0

  def run(self):
    codes = {
      0: 'ok',
      1: 'warning',
      2: 'critical',
      #3: 'unknown', # will be handled by codes.get()
    }

    (exit_code, output) = self.command.run()
    perfdata = NagiosPlugin.perfdata(output)
    data = NagiosPlugin.nagiosplugins(perfdata)
    status = codes.get(exit_code, 'unknown')

    self.last_run = time.time()

    if data is None:
      # no perfdata, short circuit
      return { # ModMon::Event v=1
        'v': 1,
        'time': int(time.time()), # no need for subsecond precision
        'location': self.location,
        'event': {
          'name': self.aspect,
          'state': {
            'value': status,
            'expected':  ['ok'],
            'attention': ['warning'],
          }
        }
      }

    warnings = dict([
      (datum['label'], datum['warn'])
      for datum in data if datum['warn'] is not None
    ])
    criticals = dict([
      (datum['label'], datum['crit'])
      for datum in data if datum['crit'] is not None
    ])
    units = dict([
      (datum['label'], datum['unit'])
      for datum in data if datum['unit'] is not None
    ])

    value_set = {
      'value': dict([ (datum['label'], datum['value']) for datum in data ])
    }
    if len(warnings) > 0 or len(criticals) > 0:
      value_set['threshold_high'] = {}
    if len(warnings) > 0:
      value_set['threshold_high']['warning'] = warnings
    if len(criticals) > 0:
      value_set['threshold_high']['critical'] = criticals
    if len(units) > 0:
      value_set['units'] = units

    event = { # ModMon::Event v=1
      'v': 1,
      'time': int(time.time()), # no need for subsecond precision
      'location': self.location,
      'event': {
        'name': self.aspect,
        'vset': value_set,
      }
    }
    # if thresholds are set, the status should reflect thresholds being
    # exceeded; if there's no thresholds (either because they're not set for
    # values or there are no values), state is to be passed
    if len(warnings) == 0 and len(criticals) == 0:
      event['event']['state'] = {
        'value': status,
        'expected':  ['ok'],
        'attention': ['warning'],
      }
    return event

  def when(self):
    return self.last_run + self.schedule

#-----------------------------------------------------------------------------

class ShellCommand:
  def __init__(self, command):
    self.command = command

  def run(self):
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
