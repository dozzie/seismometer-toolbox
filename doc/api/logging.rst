*****************
Logging functions
*****************


Python documentation to read
============================

* Python :mod:`logging`: `<https://docs.python.org/2/library/logging.html>`_
* Configuring :mod:`logging`: `<https://docs.python.org/2/library/logging.config.html>`_
* Configuring :mod:`logging` with dictionary:
  `<https://docs.python.org/2/library/logging.config.html#logging-config-dictschema>`_


Configuration examples
======================

YAML logging config (see :ref:`yaml-logging-config` for example) can be used as
follows::

   import seismometer.logging
   import yaml
   log_config = yaml.safe_load(log_config_file)
   seismometer.logging.dictConfig(log_config)

Given that logging configuration is a simple dictionary, config file is not
restricted to YAML format. See :ref:`python-logging-config` for example.

.. _python-logging-config:

Logging config dict
-------------------

.. code-block:: python

   log_config = {
       "version": 1,
       "root": { "handlers": ["stdout"] },
       "handlers": {
           "stdout": {
               "class": "logging.StreamHandler",
               "stream": "ext://sys.stdout",
               "formatter": "precise_formatter",
           },
           "syslog": {
               "class": "seismometer.logging.SysLogHandler",
               "formatter": "syslog_formatter",
               "facility": "daemon",
               # XXX: change "somethingd" to your daemon name if you plan to use
               # syslog handler
               "process_name": "somethingd"
           },
       },
       "formatters": {
           "brief_formatter": {
               "format": "%(levelname)-8s %(message)s",
           },
           "precise_formatter": {
               "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s",
               "datefmt": "<%Y-%m-%d %H:%M:%S>",
           },
           "syslog_formatter": {
               "format": "[%(name)s] %(message)s",
           },
       },
   }


.. _yaml-logging-config:

Logging config YAML
-------------------

.. code-block:: yaml

   ---
   version: 1
   root:
     handlers: [stdout]
   handlers:
     stdout:
       class: logging.StreamHandler
       stream: ext://sys.stdout
       formatter: precise_formatter
     syslog:
       class: seismometer.logging.SysLogHandler
       formatter: syslog_formatter
       facility: daemon
       # XXX: change "somethingd" to your daemon name if you plan to use
       # syslog handler
       process_name: somethingd
   formatters:
     brief_formatter:
       format: "%(levelname)-8s %(message)s"
     precise_formatter:
       format: "%(asctime)s %(levelname)-8s %(name)-15s %(message)s"
       datefmt: "%Y-%m-%d %H:%M:%S"
     syslog_formatter:
       format: "[%(name)s] %(message)s"


Programming interface
=====================

For Python 2.7, :mod:`logging.config` module has a :func:`dictConfig`
function. For older releases (2.4 through 2.6, possibly even older) Seismometer
Toolbox provides :func:`seismometer.logging.dictConfig` function that works the
same way (on Python 2.7 it's actually imported
:func:`logging.config.dictConfig`). User can configure logging following way,
regardless of the Python release::

   import seismometer.logging
   seismometer.logging.dictConfig(log_config)

.. automodule:: seismometer.logging

