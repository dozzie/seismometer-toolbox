*********
DumbProbe
*********

DumbProbe is a simple tool that checks whether all the services defined in its
config are healthy and submits the results of the checks to Panopticon.

The checks can be defined as calls to `Monitoring Plugins
<https://www.monitoring-plugins.org/>`_.

Usage
=====

Usage is pretty straightforward: one just needs to run::

   dumb-probe.py --checks=./checks.py --destination=host:port:channel

All the probe results will be sent to ``host:port`` address to Streem, to
channel ``channel``.

**NOTE**: In case on connectivity loss DumbProbe just exits and needs to be
restarted. Use :doc:`daemonshepherd`, `Monit
<http://mmonit.com/monit/>`_ or similar tool to keep DumbProbe running.

Command line options
--------------------

.. cmdoption:: --checks <checks-file>

   See :ref:`config-file`

.. cmdoption:: --destination <host>:<port>:<channel>

.. _config-file:

Configuration file
------------------

Configuration file is a Python script. The only thing expected from the script
is defining :obj:`checks` object, which in turn needs to have
:meth:`run_next` method, called with no arguments. The method is supposed
supposed to wait until the check needs to be run, run the check and return
JSON-serializable object (typically a dictionary). This object will be
submitted to Streem.

API
===

.. autoclass:: panopticon.dumbprobe.Checks
   :members:
   :undoc-members:

