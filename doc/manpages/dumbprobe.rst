*********
DumbProbe
*********

Synopsis
========

.. code-block:: none

   dumb-probe [options] --checks=<checks-file>

Description
===========

DumbProbe is a simple tool that checks whether all the services defined in its
config are healthy and submits the results of the checks to monitoring system.

The checks file is a Python module that defines what, how, and how often
should be checked. Results are packed into a Seismometer message and sent to
a :manpage:`messenger(8)` (or a compatible router).

Options
=======

.. cmdoption:: --checks <checks-file>

   Python module that defines checks. See :ref:`checks-file`.

.. cmdoption:: --destination stdout | tcp:<host>:<port> | udp:<host>:<port> | unix:<path>

   Address to send check results to.

   If unix socket is specified, it's datagram type, like
   :manpage:`messenger(8)` uses.

   If no destination was provided, messages are printed to STDOUT.

.. cmdoption:: --logging <config>

   Logging configuration file (YAML or JSON) with dictionary suitable for
   :func:`logging.config.dictConfig`. If not specified, messages (but only
   warnings) are printed to *STDERR*. See :ref:`yaml-logging-config` for
   example config.

.. _checks-file:

Configuration
=============

Configuration file is a Python module. The only thing expected from the module
is defining :obj:`CHECKS` object, which usually will be a list of check
objects (typically a :class:`seismometer.dumbprobe.BaseCheck` subclass
instances). DumbProbe will take care of scheduling runs of each of the checks
according to their specified intervals.

If there is a need for any other scheduling logic, :obj:`CHECKS` can be an
arbitrary Python object that has :meth:`run_next()` method, which is
responsible for waiting for next check and running it. This method will be
called with no arguments and should return a sequence (e.g. list) of messages
that are either :class:`seismometer.message.Message` objects or dictionaries
(serializable to JSON). These messages will be sent to DumbProbe's
destination.

Supported check types
---------------------

The simplest case of a check is a Python function that produces a dictionary,
:class:`seismometer.message.Message` object, or list of these. Such function
is wrapped in :class:`seismometer.dumbprobe.Function` object in :obj:`CHECKS`
list.

There are also several built-in classes that facilitate working with external
commands and scripts:

* :class:`seismometer.dumbprobe.ShellOutputMetric` -- command that prints
  a number (integer or float) to *STDOUT*
* :class:`seismometer.dumbprobe.ShellOutputState` -- command that prints state
  (see `message schema v3
  <http://seismometer.net/message-schema/v3/#structure>`_) to *STDOUT*
* :class:`seismometer.dumbprobe.ShellExitState` -- command that indicates
  state using exit code (*STDOUT* is discarded)
* :class:`seismometer.dumbprobe.ShellOutputJSON` -- command that prints raw
  JSON messages to *STDOUT*
* :class:`seismometer.dumbprobe.Nagios` -- command that conforms to
  `Monitoring Plugins <https://www.monitoring-plugins.org/>`_ protocol,
  including performance data for collecting metrics

Typically, checks file will look somewhat like this:

.. code-block:: python

   from seismometer.dumbprobe import *
   from seismometer.message import Message, Value
   import os

   #--------------------------------------------------------------------

   def hostname():
       return os.uname()[1]

   #--------------------------------------------------------------------

   def uptime():
       with open("/proc/uptime") as f:
           return Message(
               aspect = "uptime",
               location = {"host": hostname()},
               value = float(f.read().split()[0]),
           )

   def df(mountpoint):
       stat = os.statvfs(mountpoint)
       result = Message(
           aspect = "disk space",
           location = {
               "host": hostname(),
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

   #--------------------------------------------------------------------

   CHECKS = [
       # function called every 60s with empty arguments list
       Function(uptime, interval = 60),
       # function called every 30 minutes with a single argument
       Function(df, args = ["/"],     interval = 30 * 60),
       Function(df, args = ["/home"], interval = 30 * 60),
       Function(df, args = ["/tmp"],  interval = 30 * 60),
       # shell command (`sh -c ...'), prints list of JSON objects to
       # STDOUT
       ShellOutputJSON("/usr/local/bin/read-etc-passwd", interval = 60),
       # external command (run without `sh -c'), prints single number
       ShellOutputMetric(
           ["/usr/local/bin/random", "0.5"],
           interval = 30,
           aspect = "random",
           host = hostname(),
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
           # this one runs without shell
           ["/usr/lib/nagios/plugins/check_load", "-w", "0.25", "-c", "0.5"],
           interval = 10,
           aspect = "load average",
           host = hostname(), service = "load",
       ),
       Nagios(
           # this one runs with shell
           "/usr/lib/nagios/plugins/check_users -w 3 -c 5",
           interval = 60,
           aspect = "wtmp",
           host = hostname(), service = "users",
       ),
   ]

Programming interface
=====================

**NOTE**: User doesn't need to use these classes/functions if they happen to
not suit the needs. They are merely a proposal, but the author thinks they
should at least help somewhat in deployment.

.. automodule:: seismometer.dumbprobe

See Also
========

* message schema v3 <http://seismometer.net/message-schema/v3/>
* :manpage:`daemonshepherd(8)`
* :manpage:`messenger(8)`
* Monitoring Plugins <https://www.monitoring-plugins.org/>

