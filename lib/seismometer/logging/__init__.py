#!/usr/bin/python
'''
Logging configuration functions
-------------------------------

.. function:: dictConfig(config)

   :param config: configuration dict

   Compatibility function for setting up logging using dict, possibly loaded
   from file.

   For Python 2.7+ this function is just :func:`logging.config.dictConfig()`.
   For older releases, local copy is used.

.. autofunction:: configure_from_file

.. autofunction:: log_config_syslog

.. autofunction:: log_config_stderr

.. autofunction:: log_config_null

Log handler classes
-------------------

.. autoclass:: NullHandler

.. autoclass:: SysLogHandler

'''
#-----------------------------------------------------------------------------

import logging
import yaml
import os
import syslog

#-----------------------------------------------------------------------------

try:
    # Python 2.7+
    from logging.config import dictConfig
except ImportError:
    # older Python, use local copy of dictConfig()
    from logging_config import dictConfig

#-----------------------------------------------------------------------------

class NullHandler(logging.Handler):
    '''
    Sink log handler. Used to suppress logs.
    '''
    def __init__(self):
        super(NullHandler, self).__init__()

    def emit(self, record):
        pass

    def handle(self, record):
        pass

#-----------------------------------------------------------------------------

class SysLogHandler(logging.Handler):
    '''
    Syslog log handler. This one works a little better than
    :mod:`logging.handlers.SysLogHandler` with regard to syslog restarts and
    is independent from log socket location. On the other hand, it only logs
    to locally running syslog.

    This handler requires two fields to be provided in configuration:
    ``"facility"`` (e.g. ``"daemon"``, ``"local0"`` through
    ``"local7"``, ``"syslog"``, ``"user"``) and ``"process_name"``, which will
    identify the daemon in logs.
    '''

    # some of the facilities happen to be missing in various Python
    # installations
    _FACILITIES = dict([
        (n, getattr(syslog, "LOG_" + n.upper()))
        for n in [
            "auth", "authpriv", "cron", "daemon", "ftp", "kern",
            "local0", "local1", "local2", "local3",
            "local4", "local5", "local6", "local7",
            "lpr", "mail", "news", "syslog", "user", "uucp",
        ]
        if hasattr(syslog, "LOG_" + n.upper())
    ])
    _PRIORITIES = { # shamelessly stolen from logging.handlers:SysLogHandler
        "alert":    syslog.LOG_ALERT,
        "crit":     syslog.LOG_CRIT,
        "critical": syslog.LOG_CRIT,
        "debug":    syslog.LOG_DEBUG,
        "emerg":    syslog.LOG_EMERG,
        "err":      syslog.LOG_ERR,
        "error":    syslog.LOG_ERR,        #  DEPRECATED
        "info":     syslog.LOG_INFO,
        "notice":   syslog.LOG_NOTICE,
        "panic":    syslog.LOG_EMERG,      #  DEPRECATED
        "warn":     syslog.LOG_WARNING,    #  DEPRECATED
        "warning":  syslog.LOG_WARNING,
    }

    @classmethod
    def _priority(self, levelname):
        return self._PRIORITIES.get(levelname, syslog.LOG_WARNING)

    def __init__(self, facility, process_name):
        super(SysLogHandler, self).__init__()
        if facility not in SysLogHandler._FACILITIES:
            raise ValueError("invalid syslog facility: %s" % (facility,))
        syslog.openlog(process_name, syslog.LOG_PID,
                       SysLogHandler._FACILITIES[facility])

    def close(self):
        syslog.closelog()
        super(SysLogHandler, self).close()

    def emit(self, record):
        priority = SysLogHandler._priority(record.levelname)
        msg = self.format(record)
        if type(msg) is unicode:
            msg = msg.encode('utf-8')
        syslog.syslog(priority, msg)

#-----------------------------------------------------------------------------

def configure_from_file(filename, default = None):
    '''
    :param filename: file (JSON or YAML) to read configuration from (may be
        ``None``)
    :param default: configuration to use in case when :obj:`filename` doesn't
        exist

    Function configures logging according to dict config read from
    :obj:`filename`. If :obj:`filename` is missing and :obj:`default` was
    specified, logging is configured according to that one. If no acceptable
    :obj:`filename` nor :obj:`default` was provided, :exc:`RuntimeError` is
    raised.

    :obj:`default` should be dict config, but as a shorthand, it may be
    ``"stderr"`` or ``"null"``. Logging will be configured then with
    :func:`log_config_stderr()` or :func:`log_config_null()`,
    respectively.
    '''
    if filename is not None and os.path.isfile(filename):
        # JSON is a valid YAML, so we'll stick to this parser, we'll just make
        # sure nothing as fancy as custom classes gets loaded
        config = yaml.safe_load(open(filename))
    elif default == "stderr":
        config = log_config_stderr()
    elif default == "null":
        config = log_config_null()
    elif isinstance(default, dict):
        config = default
    else:
        raise RuntimeError('no usable logging configuration specified')
    dictConfig(config)

#-----------------------------------------------------------------------------

def log_config_syslog(procname, facility = "daemon", level = "info"):
    '''
    :param procname: name of the process to report to syslog
    :param facility: syslog facility
    :param level: log level
    :return: logging config dictionary

    Function returns logging configuration that logs to syslog messages of
    severity *info* or higher. Intended to be used with :func:`dictConfig()`.

    Some valid values for ``facility``: ``"daemon"``, ``"local0"`` through
    ``"local7"``, ``"syslog"``, ``"user"``.

    Valid log levels: ``"debug"``, ``"info"``, ``"warning"``, ``"error"``,
    ``"critical"``.
    '''
    return {
        "version": 1,
        "root": {
            "level": level.upper(),
            "handlers": ["syslog"],
        },
        "formatters": {
            "syslog_formatter": {
                "format": "[%(name)s] %(message)s",
            },
        },
        "handlers": {
            "syslog": {
                "class": "seismometer.logging.SysLogHandler",
                "formatter": "syslog_formatter",
                "facility": facility,
                "process_name": procname.strip(),
            },
        },
    }

def log_config_stderr():
    '''
    :return: logging config dictionary

    Function returns logging configuration that prints to *STDERR* logs of
    severity *warning* or higher. Intended to be used with
    :func:`dictConfig()`.
    '''
    return {
        "version": 1,
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
        "formatters": {
            "brief_formatter": {
                "format": "[%(name)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief_formatter",
                "stream": "ext://sys.stderr",
            },
        },
    }

def log_config_null():
    '''
    :return: logging config dictionary

    Function returns logging configuration that suppresses any logs
    whatsoever. Intended to be used with :func:`dictConfig()`.
    '''
    return {
        "version": 1,
        "root": {
            "level": "NOTSET",
            "handlers": ["sink"],
        },
        "handlers": {
            "sink": {
                "class": "seismometer.logging.NullHandler",
            },
        },
    }

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
