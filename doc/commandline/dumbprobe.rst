*********
DumbProbe
*********

DumbProbe is a simple tool that checks whether all the services defined in its
config are healthy and submits the results of the checks to Seismometer.

The checks can be defined as calls to `Monitoring Plugins
<https://www.monitoring-plugins.org/>`_.

Usage
=====

.. code-block:: none

   dumb-probe --checks=./checks.py [--destination=<address>]


Command line options
--------------------

.. cmdoption:: --checks <checks-file>

   See :ref:`config-file`

.. cmdoption:: --destination stdout | tcp:<host>:<port> | udp:<host>:<port> | unix:<path>

   Address to send data to.

   If no destination was provided, messages are printed to STDOUT.

.. _config-file:

Configuration file
------------------

Configuration file is a Python script. The only thing expected from the script
is defining :obj:`CHECKS` object, which may be a list of check objects
(typically a :class:`seismometer.dumbprobe.BaseCheck` subclass instances) or
an object that has :meth:`run_next()` method, which will be called with no
arguments. :class:`seismometer.dumbprobe.Checks` class is an example of what
is expected.

Example configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   from seismometer.dumbprobe import *
   from seismometer.message import Message, Value
   import os
   
   #--------------------------------------------------------------------------
   
   def uptime():
       with open("/proc/uptime") as f:
           return Message(
               aspect = "uptime",
               location = {"host": os.uname()[1]},
               value = float(f.read().split()[0]),
           )
   
   def df(mountpoint):
       stat = os.statvfs(mountpoint)
       result = Message(
           aspect = "disk space",
           location = {
               "host": os.uname()[1],
               "filesystem": mountpoint,
           },
       )
       result["free"]  = Value(
           stat.f_bfree  * stat.f_bsize / 1024.0 / 1024.0,
           unit = "MB",
       )
       result["total"] = Value(
           stat.f_blocks * stat.f_bsize / 1024.0 / 1024.0,
           unit = "MB",
       )
       return result
   
   #--------------------------------------------------------------------------
   
   CHECKS = [
       # function called every 60s with empty arguments list
       Function(uptime, interval = 60),
       # function called every 30 minutes with a single argument
       Function(df, args = ["/"],     interval = 30 * 60),
       Function(df, args = ["/home"], interval = 30 * 60),
       Function(df, args = ["/tmp"],  interval = 30 * 60),
       # shell command (`sh -c ...'), prints list of JSON objects to STDOUT
       ShellOutputJSON("/usr/local/bin/read-etc-passwd", interval = 60),
       # external command (run without `sh -c'), prints single number
       ShellOutputMetric(
           ["/usr/local/bin/random", "0.5"],
           interval = 30,
           aspect = "random",
           host = os.uname()[1],
       ),
       # external command, prints "missing" (expected) or anything else
       # (error)
       ShellOutputState(
           ["/usr/local/bin/file_exists", "/etc/nologin"],
           expected = ["missing"],
           interval = 60,
           aspect = "nologin marker",
       ),
       # and two Monitoring Plugins
       Nagios(
           # this one is run without shell
           ["nagios/plugins/check_load", "-w", "0.25", "-c", "0.5"],
           interval = 10,
           aspect = "load average",
           host = "wolfram.example.net", service = "load",
       ),
       Nagios(
           # this one is run with shell
           "/usr/lib/nagios/plugins/check_users -w 3 -c 5",
           interval = 60,
           aspect = "wtmp",
           host = "wolfram.example.net", service = "users",
       ),
   ]

Programming interface
=====================

**NOTE**: User doesn't need to use these classes/functions if they happen to
not suit the needs. They are merely a proposal, but the authors think they
should at least help somewhat in deployment.

.. automodule:: seismometer.dumbprobe

