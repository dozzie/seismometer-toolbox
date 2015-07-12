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

.. autoclass:: NullHandler

'''
#-----------------------------------------------------------------------------

import logging
import yaml
import os

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
                "format": procname.strip() + \
                          "[%(process)d]: [%(name)s] %(message)s",
            },
        },
        "handlers": {
            "syslog": {
                "class": "logging.handlers.SysLogHandler",
                "formatter": "syslog_formatter",
                "address": "/dev/log",
                "facility": facility,
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
