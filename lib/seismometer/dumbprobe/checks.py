#!/usr/bin/python
'''
Available checks
----------------

.. autoclass:: BaseCheck
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

.. autoclass:: Function
   :members:

'''
#-----------------------------------------------------------------------------

import time
import subprocess
import seismometer.message

__all__ = [
    'BaseCheck',
    'ShellOutputJSON', 'ShellOutputMetric', 'ShellOutputState',
    'ShellExitState', 'Nagios',
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
        :param kwargs: additional keys to be added to ``location`` (kwargs
           take precedence over individual values in ``location``)

        Fields defined by this class:

        .. attribute:: interval

           interval at which this check should be run, in seconds

        .. attribute:: last_run

           last time when this check was run (epoch timestamp)

        .. attribute:: aspect

           name of monitored aspect to be set

        .. attribute:: location

           location to be set (dict ``str => str``)

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

class ShellOutputJSON(BaseCheck):
    '''
    Plugin to run external command and collect its *STDOUT* as a message.

    The command is expected to print JSON, and this JSON is returned
    unmodified. Command may output more than one JSON object, all of them will
    be returned as check results.
    '''
    def __init__(self, command, **kwargs):
        '''
        :param command: command to run (string for shell command, or list of
           strings for direct command to run)
        '''
        super(ShellOutputJSON, self).__init__(**kwargs)

    def run(self):
        self.mark_run()
        return None

class ShellOutputMetric(BaseCheck):
    '''
    Plugin to collect metric from *STDOUT* of a command.

    The command is expected to print just a number (integer or floating
    point).
    '''
    def __init__(self, command, aspect, **kwargs):
        '''
        :param command: command to run (string for shell command, or list of
           strings for direct command to run)
        :param aspect: aspect name, as in :class:`seismometer.message.Message`
        '''
        super(ShellOutputMetric, self).__init__(**kwargs)

    def run(self):
        self.mark_run()
        return None

class ShellOutputState(BaseCheck):
    '''
    Plugin to collect state from *STDOUT* of a command.

    The command should print the state as a single word. The state is then
    checked against expected states to determine its severity.
    '''
    def __init__(self, command, aspect, **kwargs):
        '''
        :param command: command to run (string for shell command, or list of
           strings for direct command to run)
        :param aspect: aspect name, as in :class:`seismometer.message.Message`
        '''
        super(ShellOutputState, self).__init__(**kwargs)

    def run(self):
        self.mark_run()
        return None

class ShellExitState(BaseCheck):
    '''
    Plugin to collect state from exit code of a command.

    Exit code of 0 renders ``ok, expected`` message, any other renders
    ``exit_$?, error`` or ``$signame, error`` (``$?`` being the actual exit
    code and ``$signame`` name of signal, like ``sighup`` or ``sigsegv``).
    '''
    def __init__(self, command, aspect, **kwargs):
        '''
        :param command: command to run (string for shell command, or list of
           strings for direct command to run)
        :param aspect: aspect name, as in :class:`seismometer.message.Message`
        '''
        super(ShellExitState, self).__init__(**kwargs)

    def run(self):
        self.mark_run()
        return None

class Nagios(BaseCheck):
    '''
    Plugin to collect state and possibly metrics from a `Monitoring Plugin
    <https://www.monitoring-plugins.org/>`_.

    Metrics to be recognized need to be specified as described in section
    *Performance data* of `Monitoring Plugins Development Guidelines
    <https://www.monitoring-plugins.org/doc/guidelines.html>`_.
    '''
    def __init__(self, plugin, aspect, **kwargs):
        '''
        :param plugin: command to run (string for shell command, or list of
           strings for direct command to run)
        :param aspect: aspect name, as in :class:`seismometer.message.Message`
        '''
        super(Nagios, self).__init__(**kwargs)

    def run(self):
        self.mark_run()
        return None

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

#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
