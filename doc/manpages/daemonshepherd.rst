****************
*daemonshepherd*
****************

Synopsis
========

.. code-block:: none

   daemonshepherd [options] --daemons=<specfile>
   daemonshepherd [options] reload
   daemonshepherd [options] list
   daemonshepherd [options] start <daemon-name>
   daemonshepherd [options] stop <daemon-name>
   daemonshepherd [options] restart <daemon-name>
   daemonshepherd [options] cancel-restart <daemon-name>
   daemonshepherd [options] list-commands <daemon-name>
   daemonshepherd [options] command <daemon-name> <command-name>

Description
===========

*daemonshepherd* is a tool for keeping other tools running. This task consists
of starting the tools, capturing their *STDOUT* and restarting them if they
die. This way user can focus on work the tool needs to do instead of
reimplementing daemonization and logging over and over again.

Usage
=====

Running *daemonshepherd* without any command starts a daemon supervisor mode.
By default, *daemonshepherd* runs in the foreground and prints warnings to
*STDERR*. Option :option:`--daemons` is required in this mode.

.. _daemonshepherd-commands:

Commands
--------

.. describe:: daemonshepherd list

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

.. describe:: daemonshepherd cancel-restart <daemon-name>

   cancels pending restart of specified daemon

.. describe:: daemonshepherd list-commands <daemon-name>

   list administrative commands defined for this daemon

.. describe:: daemonshepherd command <daemon-name> <command-name>

   runs an administrative command defined for specified daemon

Options
-------

Most of the options are only meaningful when *daemonshepherd* runs as
a supervisor. The exception is :option:`--socket`, which specifies
administrative socket of a running *daemonshepherd*.

.. program:: daemonshepherd

.. option:: -f <specfile>, --daemons <specfile>

   specification of daemons to start (see :ref:`daemonshepherd-specfile` for
   details)

.. option:: -l <config>, --logging <config>

   logging configuration, in JSON or YAML format (see
   :ref:`daemonshepherd-logging` for details); default is to log to *STDERR*
   or to syslog (:option:`--background`)

.. option:: --silent

   don't log anywhere; this option is overriden by :option:`--logging`

.. option:: --stderr

   log to *STDERR*; this option is overriden by :option:`--logging`

.. option:: --syslog

   log to syslog; this option is overriden by :option:`--logging`

.. option:: -s <path>, --socket <path>

   unix socket path to listen for administrative commands

.. option:: -p <path>, --pid-file <path>

   path to file with PID of *daemonshepherd* instance

.. option:: -d, --background

   detach from terminal and change working directory to :file:`/`

.. option:: -u <user>, --user <user>

   user to run as

.. option:: -g <group>, --group <group>

   group to run as

.. _daemonshepherd-specfile:

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
  command, too); daemon is started in its own process group and should not try
  to detach from terminal
* ``argv0`` -- custom process name (``argv[0]``), though under Linux it's
  a little less useful than it sounds (only shows with some :manpage:`ps(1)`
  invocations, like ``ps -f``)
* ``stop_signal`` -- signal (number or name, like SIGTERM or TERM) to stop
  the daemon; if specified, it's delivered to the daemon process only, if not
  specified, defaults to *SIGTERM* and is delivered to the daemon's process
  group
* ``stop_command`` -- command used to stop running daemon; it will be
  executed with the same environment and working directory as
  ``start_command``, with :envvar:`$DAEMON_PID` set to PID of the daemon; if
  both ``stop_signal`` and ``stop_command`` are defined, ``stop_command`` has
  the precedence
* ``user``, ``group`` -- username and group name to run as (both
  ``start_command`` and ``stop_command`` will be run with these
  credentials); ``group`` can be a list of group names; obviously this
  requires *daemonshepherd* to be run as root
* ``cwd`` -- working directory to start daemon in
* ``environment`` -- additional environment variables to set (useful for
  setting :envvar:`$PYTHONPATH` or similar)
* ``stdout`` -- what to do with daemon's *STDOUT* and *STDERR*; following
  values are recognized:

  * ``console`` or undefined -- pass the output directly to terminal
  * ``/dev/null`` -- redirect output to :file:`/dev/null`
  * ``log`` -- intercept *STDOUT*/*STDERR* and log it with :mod:`logging`
    module; output will be logged by logger ``daemon.<name>``, so it can be
    filtered in logging configuration

* ``restart`` -- restart strategy; see :ref:`daemonshepherd-restart-strategy`
  section for details
* ``start_priority`` -- start priority (lower number starts earlier);
  defaults to 10
* ``commands`` -- additional administrative commands for the daemon;
  see :ref:`daemonshepherd-daemon-admin-commands` section for details

Default values for above-mentioned variables can be stored in ``defaults``
hash.

**NOTE**: ``environment`` key will be *replaced* by daemon's value, not
*merged*. It's not possible to add just one environment variable.

.. _daemonshepherd-daemon-admin-commands:

Daemon's administrative commands
--------------------------------

Daemon can have available some special commands, like reloading configuration
or reopening log files. Such commands are defined under ``commands`` field in
daemon specification.

A command can specify either a command to run or a signal to send. Some of the
variables that can be set for daemon itself can also be set for a command, and
if unset, the command inherits the value from daemon. Allowed variables are:
``user``, ``group``, ``cwd``, ``environment``, ``argv0``.

By default, a command that specifies signal delivers the signal only to the
daemon process. This can be changed by setting ``process_group`` to ``true``.

Command's environment will have :envvar:`$DAEMON_PID` set to daemon's PID (or
empty string, if the daemon is not running).

**NOTE**: *daemonshepherd* will wait for administrative commands to terminate,
so they should not be long-running operations.

.. code-block:: yaml

   daemons:
     example-daemon:
       user: nobody
       start_command: /usr/sbin/example-daemon ...
       commands:
         before-start:
           user: root
           command: >-
             mkdir -p /var/log/example;
             chown nobody: /var/log/example
         reload:
           signal: SIGHUP
         rotate-logs:
           user: root
           command: >-
             : > /var/log/example/daemon.log;
             kill -USR1 $DAEMON_PID
         murder:
           signal: SIGKILL
           process_group: true

With the configuration above an operator now can call following commands:

.. code-block:: none

  $ daemonshepherd command example-daemon reload
  $ daemonshepherd command example-daemon rotate-logs
  $ daemonshepherd command example-daemon murder

There are few commands with special meaning:

* ``stop`` -- command that will be used to stop the daemon; setting
  ``stop_command`` or ``stop_signal`` is a shorthand for defining this command
* ``before-start`` -- command that will be executed just before the daemon is
  started or restarted; non-zero exit code prevents the daemon from being
  started; handy for creating socket directory in :file:`/var/run` for
  a daemon that otherwise runs as a non-privileged user
* ``after-crash`` -- command that will be executed immediately after the
  daemon's unexpected termination (but not after ``before-start`` failed); the
  command will have set either :envvar:`$DAEMON_EXIT_CODE` or
  :envvar:`$DAEMON_SIGNAL` environment variable, depending on how the daemon
  terminated

Note that these commands can be invoked in the same manner as any other
administrative command, e.g. ``daemonshepherd command $daemon after-crash``,
even though they're not expected to make sense in this situation.

.. _daemonshepherd-restart-strategy:

Restart strategy
----------------

When a daemon dies, it's restarted after a backoff time. If it dies again,
next backoff interval will be used. A list of backoff intervals (expressed as
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
:mod:`seismometer.daemonshepherd.controller` module for reference).

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
           --src=unix:/var/run/messenger/socket
           --dest=tcp:10.4.5.11:24222
           --tagfile=/etc/seismometer/messenger.tags
           --logging=/etc/seismometer/messenger.logging
       commands:
         pre-start:
           user: root
           command: >-
             mkdir -p -m 755 /var/run/messenger;
             chown seismometer:seismometer /var/run/messenger
     dumbprobe:
       # string folded for readability
       start_command: >-
           dumb-probe
           --checks=/etc/seismometer/dumbprobe.py
           --dest=unix:/var/run/messenger/socket
           --logging=/etc/seismometer/dumbprobe.logging

     # some daemon that needs to be shut down by command instead of by
     # SIGTERM
     statetip:
       start_priority: 1
       cwd: /var/lib/statetip
       environment:
         ERL_LIBS: /usr/lib/statetip
       # strings folded for readability
       start_command: >-
           statetipd start
           --socket=/var/run/statetip/control
           --config=/etc/statetip.conf
       # shorthand for "commands.stop"
       stop_command: >-
           statetipd stop
           --socket=/var/run/statetip/control
       commands:
         pre-start:
           user: root
           command: >-
             mkdir -p -m 750 /var/run/statetip;
             chown seismometer:seismometer /var/run/statetip
         reload:
           command: statetipd reload --socket=/var/run/statetip/control
         brutal-kill:
           signal: SIGKILL

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
           /etc/seismometer/bin/count-clients
           | socat - unix:/var/run/collectd/clients.sock

.. _daemonshepherd-logging:

Logging configuration
=====================

.. include:: logging.rst.common

Signals
=======

*daemonshepherd* recognizes following signals:

* *SIGTERM* and *SIGINT* cause termination
* *SIGHUP* causes reloading daemons specification

