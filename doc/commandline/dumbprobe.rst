*********
DumbProbe
*********

DumbProbe is a simple tool that checks whether all the services defined in its
config are healthy and submits the results of the checks to Seismometer.

The checks can be defined as calls to `Monitoring Plugins
<https://www.monitoring-plugins.org/>`_.

Usage
=====

Usage is pretty straightforward: one just needs to run:

.. code-block:: none

   dumb-probe --checks=./checks.py --destination=host:port:channel

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

   Streem to submit data to.

.. _config-file:

Configuration file
------------------

Configuration file is a Python script. The only thing expected from the script
is defining :obj:`checks` object, which in turn needs to have
:meth:`run_next` method, called with no arguments. The method is supposed
supposed to wait until the check needs to be run, run the check and return
JSON-serializable object (typically a dictionary). This object will be
submitted to Streem.

Example configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   from seismometer.dumbprobe import Checks

   checks = Checks()
   checks.add(
     # this one is run with shell
     command = "/usr/lib/nagios/plugins/check_users -w 3 -c 5",
     type = 'nagios',
     host = "wolfram.example.net", aspect = "wtmp", service = "users",
     schedule = 35, # every 35s
   )
   checks.add(
     # this one is run without shell
     command = ["/usr/lib/nagios/plugins/check_load", "-w", "0.25", "-c", "0.5"],
     type = 'nagios',
     host = "wolfram.example.net", aspect = "load average", service = "load",
     schedule = 10, # every 10s
   )

API
===

**NOTE**: User doesn't need to use these classes/functions if they happen to
not suit the needs. They are merely a proposal, but the authors they should at
least help somewhat in deployment.

.. automodule:: seismometer.dumbprobe

