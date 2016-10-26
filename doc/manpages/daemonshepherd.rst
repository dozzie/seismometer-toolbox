****************
*daemonshepherd*
****************

Synopsis
========

.. code-block:: none

   daemonshepherd [options] --daemons=<specfile>
   daemonshepherd [options] reload
   daemonshepherd [options] ps
   daemonshepherd [options] start <daemon-name>
   daemonshepherd [options] stop <daemon-name>
   daemonshepherd [options] restart <daemon-name>
   daemonshepherd [options] cancel_restart <daemon-name>

Description
===========

*daemonshepherd* is a tool for keeping other tools running. This task consists
of starting the tools, capturing their *STDOUT* and restarting them if they
die. This way user can focus on work the tool needs to do instead of
reimplementing daemonization and logging over and over again.

Usage
=====

Running *daemonshepherd* without any command starts a daemon supervisor mode.
By default, *daemonshepherd* runs in the foreground and suppresses all logs.
Option :option:`--daemons` is required in this mode.

.. _daemonshepherd-commands:

Commands
--------

Except for ``ps``, administrative commands print nothing and exit with 0 on
success.

.. describe:: daemonshepherd ps

   lists daemons that are currently defined, one JSON per line

.. describe:: daemonshepherd reload

   instructs *daemonshepherd* to reload its configuration; the same as sending
   *SIGHUP* signal

.. describe:: daemonshepherd start <daemon-name>

   starts the specified daemon

.. describe:: daemonshepherd stop <daemon-name>

   stops the specified daemon

.. describe:: daemonshepherd restart <daemon-name>

   restarts the specified daemon

.. describe:: daemonshepherd cancel_restart <daemon-name>

   cancels pending restart of specified daemon

Options
-------

Most of the options are only meaningful when *daemonshepherd* runs as
a supervisor. The exception is :option:`--control-socket`, which specifies
administrative socket of a running *daemonshepherd*.

.. option:: -f <specfile>, --daemons <specfile>

   specification of daemons to start (see :ref:`specfile` for details)

.. option:: -l <config>, --logging <config>

   logging configuration, in JSON or YAML format (see
   :ref:`yaml-logging-config` for example structure)

.. option:: -s <path>, --control-socket <path>

   unix socket path to listen for administrative commands

.. option:: -p <path>, --pid-file <path>

   path to file with PID of *daemonshepherd* instance

.. option:: -d, --background

   detach from terminal and change working directory to :file:`/`

.. option:: -u <user>, --user <user>

   user to run as

.. option:: -g <group>, --group <group>

   group to run as

.. _specfile:

Configuration
=============

Daemons specfile (YAML format) describes how to start and stop supervised
daemons. Such specfile may look like this:

.. code-block:: yaml

   defaults:
     environment:
       PYTHONPATH: lib

   daemons:
     collectd:
       user: collectd
       start_command: /usr/sbin/collectd -f -C ...
     # ...

Daemons in specfile are defined under hash called ``daemons``. Each daemon has
a name, by which it will be referred to in administrative commands (see
:ref:`daemonshepherd-commands`).

A daemon can have following variables:

* ``start_command`` -- command used to start the daemon (can be a shell
  command, too); daemon should not try to detach from terminal
* ``stop_signal`` -- signal (number or name, like SIGTERM or TERM) to stop
  the daemon; defaults to *SIGTERM*
* ``stop_command`` -- command used to stop running daemon; it will be
  executed with the same environment and working directory as
  ``start_command``; if both ``stop_signal`` and ``stop_command`` are
  defined, ``stop_command`` has the precedence
* ``user``, ``group`` -- username and group name to run as (both
  ``start_command`` and ``stop_command`` will be run with these
  credentials); obviously this requires *daemonshepherd* to be run as root
* ``cwd`` -- working directory to start daemon in
* ``environment`` -- additional environment variables to set (useful for
  setting :envvar:`$PYTHONPATH` or similar)
* ``stdout`` -- what to do with daemon's *STDOUT* and *STDERR*; following
  values are recognized:

  * ``stdout`` or undefined -- pass the output to terminal
  * ``/dev/null`` -- redirect output to :file:`/dev/null`
  * ``log`` -- intercept *STDOUT*/*STDERR* and log it with :mod:`logging`
    module (**TODO**)

* ``restart`` -- restart strategy; see :ref:`restart-strategy` section for
  details
* ``start_priority`` -- start priority (lower number starts earlier);
  defaults to 10

Default values for above-mentioned variables can be stored in ``defaults``
hash.

**NOTE**: ``environment`` key will be *replaced* by daemon's value, not
*merged*. It's not possible to add just one environment variable.

.. _restart-strategy:

Restart strategy
----------------

When a daemon dies, it's restarted after backoff time. If it dies again, next
backoff interval will be used. A list of backoff intervals (expressed as
number of seconds before next try) is called a *restart strategy*. Typically
it would be a increasing list of integers, so on first death daemon is
restarted soon, but if it keeps dying, it will be restarted less often to
limit the machine's load.

After reaching the last interval ``R`` from the strategy, daemon is restarted
every ``R`` seconds until success.

If the child is running long enough (how long depends on current position in
restart strategy), restart strategy is reset.

If no restart strategy is defined (neither specific to daemon nor in
``defaults``), assumed default is ``[0, 5, 15, 30, 60]`` (see
:mod:`seismometer.daemonshepherd.controller.RestartQueue` Python class for
reference).

Example daemon spec file
------------------------

This is an example specification file that starts a set of tools to collect
monitoring data (``dumb-probe``), pass messages to another server
(``messenger``), or store metrics (`collectd <http://collectd.org>`_).

.. code-block:: yaml

   defaults:
     stdout: /dev/null
     environment:
       PYTHONPATH: /usr/lib/seismometer/toolbox
     user: seismometer
     group: seismometer

   daemons:
     # Seismometer Toolbox' own daemons: message router and monitoring
     # probe
     messenger:
       start_priority: 1
       # string folded for readability
       start_command: >-
           messenger
           --src=unix:/var/run/messenger.sock
           --dest=tcp:10.4.5.11:24222
           --tagfile=/etc/seismometer/messenger.tags
           --logging=/etc/seismometer/messenger.logging
     dumbprobe:
       # string folded for readability
       start_command: >-
           dumb-probe
           --checks=/etc/seismometer/dumbprobe.py
           --dest=unix:/var/run/messenger.sock
           --logging=/etc/seismometer/dumbprobe.logging

     # some daemon that needs to be shut down by command instead of by
     # SIGTERM
     statetip:
       start_priority: 1
       cwd: /var/lib/statetip
       environment:
         ERL_LIBS: /usr/lib/statetip
       start_command: statetipd --socket=/var/run/statetip/control start --config=/etc/statetip.conf
       stop_command: statetipd --socket=/var/run/statetip/control stop

     # custom collectd instance
     collectd:
       start_priority: 1
       user: collectd
       start_command: /usr/sbin/collectd -f -C /etc/collectd/clients.conf
     # a script that counts clients and formats the stats for collectd's
     # protocol; `socat' tool is obviously necessary here
     store-clients:
       # string folded for readability
       start_command: >-
           /etc/seismometer/bin/count-clients |
           socat - unix:/var/run/collectd/clients.sock

Signals
=======

*daemonshepherd* recognizes following signals:

* *SIGTERM* and *SIGINT* cause termination
* *SIGHUP* causes reloading daemons specification

