******************
Panopticon logging
******************

   * Python :mod:`logging`: `<https://docs.python.org/2/library/logging.html>`_
   * Configuring :mod:`logging`: `<https://docs.python.org/2/library/logging.config.html>`_
   * Configuring :mod:`logging` with dictionary:
     `<https://docs.python.org/2/library/logging.config.html#logging-config-dictschema>`_


Logging config file
===================

YAML logging config (see :ref:`yaml-config` for example) can be used as
follows::

   import yaml
   log_config = yaml.safe_load(log_config_file)
   dictConfig(log_config)

.. _python-config:

Python dictionary
-----------------

.. code-block:: python

   log_config = {
     "version": 1,
     "root": { "handlers": ["stdout"] },
     "handlers": {
       "stdout": {
         "class": "logging.StreamHandler",
         "stream": "ext://sys.stdout",
         "formatter": "precise_formatter",
       }
     },
     "formatters": {
       "brief_formatter": {
         "format": "%(levelname)-8s %(message)s",
       },
       "precise_formatter": {
         "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s",
         "datefmt": "<%Y-%m-%d %H:%M:%S>",
       },
     },
   }


.. _yaml-config:

YAML file
---------

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
   formatters:
     brief_formatter:
       format: "%(levelname)-8s %(message)s"
     precise_formatter:
       format: "%(asctime)s %(levelname)-8s %(name)-15s %(message)s"
       datefmt: "%Y-%m-%d %H:%M:%S"


API
===

For Python 2.7, :mod:`logging.config` module has a :func:`dictConfig`
function. For older releases (2.4 through 2.6, possibly even older) Panopticon
Toolbox provides :func:`panopticon.logging.dictConfig` function that works the
same way (on Python 2.7 it's actually imported
:func:`logging.config.dictConfig`). User can configure logging following way,
regardless of the Python release::

   import panopticon.logging
   panopticon.logging.dictConfig(log_config)

.. function:: panopticon.logging.dictConfig(config)

   :param config: configuration read from a file

