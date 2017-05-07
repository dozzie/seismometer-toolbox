#!/usr/bin/python
'''
Available checks
----------------

.. autoclass:: BaseCheck
   :members:

.. autoclass:: ShellCommand
   :members:

.. autoclass:: Nagios
   :members:

.. autoclass:: Function
   :members:

'''
#-----------------------------------------------------------------------------

import time
import re
import json
import signal
import logging
import subprocess
import seismometer.message

__all__ = [
    'BaseCheck',
    'ShellCommand', 'Nagios',
    'Function',
]

#-----------------------------------------------------------------------------
# base class for checks {{{

class BaseCheck(object):
    '''
    Base class for checks.
    '''
    def __init__(self, interval, aspect = None, location = {}, **kwargs):
        '''
        :param interval: number of seconds between consequent checks
        :param aspect: aspect name, as in :class:`seismometer.message.Message`
        :param location: ``str => str`` dictionary, as in
            :class:`seismometer.message.Message`
        :param kwargs: additional keys to be added to :obj:`location`

        If :obj:`aspect`, :obj:`location`, or :obj:`kwargs` are provided, all
        the messages produced by :meth:`run()` are expected to be either
        :class:`seismometer.message.Message` instances or dictionaries
        conforming to the message schema. Both :obj:`aspect` and individual
        values from :obj:`location` overwrite whatever was set in the produced
        messages.

        Fields defined by this class:

        .. attribute:: interval

           interval at which this check should be run, in seconds

        .. attribute:: last_run

           last time when this check was run (epoch timestamp)

        .. attribute:: aspect

           name of monitored aspect to be set

        .. attribute:: location

           location to be set (dictionary ``str => str``)

        .. method:: check_name()

           :return: check's name
           :rtype: string

           Method not really defined in this class. If a subclass defines this
           method, it will be called to get a name of a check the object
           represents. If left undefined, default name composed of class name,
           module, and object's :func:`id()` will be used.

        '''
        self.interval = interval
        self.aspect = aspect
        self.location = location.copy()
        self.location.update(kwargs)
        # XXX: it's epoch time; let's assume January 1970 is a good -infinity
        self.last_run = 0

    def run(self):
        '''
        :return: check result
        :rtype: :class:`seismometer.message.Message`, dict, list of these, or
            ``None``

        Run the check.

        Implementing method should manually call :meth:`mark_run()` for
        :meth:`next_run()` to work correctly. To limit problems with
        unexpected exceptions, :meth:`mark_run()` should be run just at the
        beginning.
        '''
        raise NotImplementedError("method run() not implemented")

    def mark_run(self):
        '''
        Update last run timestamp.
        '''
        self.last_run = time.time()

    def next_run(self):
        '''
        :return: epoch time when the check should be run next time
        '''
        return self.last_run + self.interval

    def _populate(self, message):
        '''
        Helper to add aspect name and location to message, whatever it is.
        '''
        if isinstance(message, seismometer.message.Message):
            if self.aspect is not None:
                message.aspect = self.aspect
            for (l,v) in self.location.iteritems():
                message.location[l] = v
        else: # dict
            if self.aspect is not None:
                # XXX: if message['event'] does't exist, it's not valid
                # SSMM.Msg v3, so "aspect" term doesn't have any sense
                message['event']['name'] = self.aspect
            if len(self.location) > 0:
                message['location'].update(self.location)
        return message

# }}}
#-----------------------------------------------------------------------------
# plugins that call external commands {{{

class ShellCommand(BaseCheck):
    '''
    Plugin to run external command and process its *STDOUT* and exit code with
    a separate function.
    '''
    def __init__(self, command, parse, **kwargs):
        '''
        :param command: command to run (string for shell command, or list of
            strings for direct command to run)
        :param parse: function to process command's output
        :param kwargs: keyword arguments to pass to :class:`BaseCheck`
            constructor

        :obj:`parse` should be a function (or callable) that accepts two
        positional arguments: first one will be command's *STDOUT*, the second
        will be command's exit code (or termination signal, if negative).
        '''
        super(ShellCommand, self).__init__(**kwargs)
        self.command = command
        self.parse = parse
        self.use_shell = not isinstance(command, (list, tuple))

    def run(self):
        self.mark_run()
        (exitcode, stdout) = run(self.command, self.use_shell)
        result = self.parse(stdout, exitcode)
        return [self._populate(m) for m in each(result)]

class Nagios(BaseCheck):
    '''
    Plugin to collect state and possibly metrics from a `Monitoring Plugin
    <https://www.monitoring-plugins.org/>`_.

    Metrics to be recognized need to be specified as described in section
    *Performance data* of `Monitoring Plugins Development Guidelines
    <https://www.monitoring-plugins.org/doc/guidelines.html>`_.
    '''
    _PERFDATA = re.compile(
        "(?P<label>[^ '=]+|'(?:[^']|'')*')="     \
        "(?P<value>[0-9.]+)"                     \
        "(?P<unit>[um]?s|%|[KMGT]?B|c)?"         \
            "(?:;(?P<warn>[0-9.]*)"              \
                "(?:;(?P<crit>[0-9.]*)"          \
                    "(?:;(?P<min>[0-9.]*)"       \
                        "(?:;(?P<max>[0-9.]*))?" \
                    ")?" \
                ")?" \
            ")?"
    )
    _EXIT_CODES = {
        0: ('ok', 'expected'),
        1: ('warning', 'warning'),
        2: ('critical', 'error'),
        #3: ('unknown', 'error'), # will be handled by codes.get()
    }
    def __init__(self, plugin, aspect, **kwargs):
        '''
        :param plugin: command to run (string for shell command, or list of
            strings for direct command to run)
        :param aspect: aspect name, as in :class:`seismometer.message.Message`
        '''
        super(Nagios, self).__init__(aspect = aspect, **kwargs)
        self.plugin = plugin
        self.use_shell = not isinstance(plugin, (list, tuple))

    def run(self):
        self.mark_run()

        (code, stdout) = run(self.plugin, self.use_shell)
        (state, severity) = Nagios._EXIT_CODES.get(code, ('unknown', 'error'))
        message = seismometer.message.Message(
            state = state, severity = severity,
            aspect = self.aspect,
            location = self.location,
        )

        status_line = stdout.split('\n')[0]
        if '|' not in status_line:
            # nothing more to parse
            return message

        metrics = []
        perfdata = status_line.split('|', 1)[1].strip()
        while perfdata != '':
            match = Nagios._PERFDATA.match(perfdata)
            if match is None: # non-plugins-conforming perfdata, abort
                return message
            metrics.append(match.groupdict())
            perfdata = perfdata[match.end():].lstrip()

        #---------------------------------------------------
        # helper functions {{{

        def number(string):
            if string == "":
                return None
            elif "." in string:
                return float(string)
            else:
                return int(string)

        def make_value(metric):
            # create a value
            value = seismometer.message.Value(number(metric['value']))
            if metric['warn'] != "":
                value.set_above(number(metric['warn']), "warning", "warning")
            if metric['crit'] != "":
                value.set_above(number(metric['crit']), "critical", "error")
            if metric['unit'] != "":
                value.unit = metric['unit']

            # extract value's name
            if metric['label'].startswith("'"):
                name = metric['label'][1:-1].replace("''", "'")
            else:
                name = metric['label']

            return (name, value)

        # }}}
        #---------------------------------------------------

        for metric in metrics:
            (name, value) = make_value(metric)
            message[name] = value
            # if any of the values has thresholds, state is expected to be
            # derivable from those thresholds
            if value.has_thresholds():
                del message.state # safe to do multiple times

        return message

# }}}
#-----------------------------------------------------------------------------
# Python function check {{{

class Function(BaseCheck):
    '''
    Plugin to collect a message to send by calling a Python function (or any
    callable).

    Function is expected to return a dict,
    :class:`seismometer.message.Message`, a list of these, or ``None``.
    '''
    def __init__(self, function, args = [], kwargs = {}, **_kwargs):
        '''
        :param interval: number of seconds between consequent checks
        :param function: function to run
        :param args: positional arguments to pass to the function call
        :param kwargs: keyword arguments to pass to the function call
        :param _kwargs: keyword arguments to pass to :class:`BaseCheck`
            constructor
        '''
        super(Function, self).__init__(**_kwargs)
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def check_name(self):
        if hasattr(self.function, "func_name"):
            return self.function.func_name + "()"
        else:
            return "F-%08X/%s.%s" % (
                id(self.function),
                self.function.__class__.__module__,
                self.function.__class__.__name__,
            )

    def run(self):
        self.mark_run()
        result = self.function(*self.args, **self.kwargs)
        if len(self.location) == 0 and self.aspect is None:
            return result
        return [self._populate(m) for m in each(result)]

# }}}
#-----------------------------------------------------------------------------

def each(msglist):
    if isinstance(msglist, (dict, seismometer.message.Message)):
        yield msglist
    elif isinstance(msglist, (list, tuple)):
        for msg in msglist:
            yield msg
    else:
        raise ValueError("invalid message (%s)" % (type(msglist),))

def run(command, use_shell):
    # TODO: what to do with STDERR?
    proc = subprocess.Popen(
        command,
        stdin = open("/dev/null"),
        stdout = subprocess.PIPE,
        shell = use_shell,
    )
    (stdout, stderr) = proc.communicate()
    # returncode <  0 -- signal
    # returncode >= 0 -- exit code
    return (proc.returncode, stdout)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
