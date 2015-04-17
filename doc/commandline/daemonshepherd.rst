****************
*daemonshepherd*
****************

*daemonshepherd* is a tool for keeping other tools running. This task consists
of starting the tools, capturing their *STDOUT* and restarting them if they
die. This way user can focus on work the tool needs to do instead of
reimplementing daemonization and logging over and over again.


Usage
=====

Running *daemonshepherd* as a supervisor for other daemons:

.. code-block:: none

   daemonshepherd.py [options] --daemons=<specfile>

Basic operation doesn't detach *daemonshepherd* from terminal and logging goes
to :file:`/dev/null`.

Controlling an already running *daemonshepherd* instance:

.. code-block:: none

   daemonshepherd.py [options] reload
   daemonshepherd.py [options] ps
   daemonshepherd.py [options] start <daemon-name>
   daemonshepherd.py [options] stop <daemon-name>
   daemonshepherd.py [options] restart <daemon-name>
   daemonshepherd.py [options] cancel_restart <daemon-name>

Command line options
--------------------

These options are only meaningful when *daemonshepherd* runs as a supervisor,
with the exception of :option:`--control-socket`, which tells the command line
tool where to send commands to.

.. cmdoption:: -f <specfile>, --daemons <specfile>

   specification of daemons to start (see :ref:`specfile` for details)

.. cmdoption:: -l <config>, --logging <config>

   logging configuration, in JSON or YAML format

.. cmdoption:: -s <path>, --control-socket <path>

   UNIX socket path to listen for commands (see :ref:`command-channel`)

.. cmdoption:: -p <path>, --pid-file <path>

   path to file with PID of *daemonshepherd* instance

.. cmdoption:: -d, --background

   detach from terminal and change working directory to :file:`/`

.. cmdoption:: -u <user>, --user <user>

   user to run as

.. cmdoption:: -g <group>, --group <group>

   group to run as


Control commands
----------------

Control commands mimic the protocol of :ref:`command channel
<command-channel>`. Except for ``ps``, they print nothing and exit with 0 on
success.

   * ``reload`` -- instructs *daemonshepherd* to reload its configuration,
     the same as sending *SIGHUP* signal
   * ``ps`` -- lists daemons that are currently defined, one JSON per line
   * ``start`` -- starts the specified daemon
   * ``stop`` -- stops the specified daemon
   * ``restart`` -- restarts the specified daemon
   * ``cancel_restart`` -- cancels pending restart of specified daemon


Signals
-------

*daemonshepherd* recognizes following signals:

   * *SIGTERM* and *SIGINT* cause termination
   * *SIGHUP* causes reloading daemons specification


.. _command-channel:

Command channel
===============

Command channel is a UNIX socket, with which operator can issue commands and
control behaviour of *daemonshepherd*.

Protocol
--------

Protocol is a synchronous exchange of JSON documents, each in its own line.

Command name is specified as ``command`` key and arguments, if any, are passed
as keys along with ``command``.

Response is a document ``{"status": "ok"}`` or
``{"status": "ok", "result": ...}``, depending on the command called. Errors
are signaled with ``{"status": "error", "reason": "..."}``.

Available commands
------------------

   * ``{"command": "reload"}`` -- reload daemons definition file

      * no data returned, just ``{"status": "ok"}``

   * ``{"command": "ps"}`` -- list daemons names (all that were defined in
     configuration, currently running ones and the ones with restart pending)

      * response result:
        ``{"result": [<info1>, <info2>, ...], "status": "ok"}``
      * ``<infoX>>`` is a hash containing information about the daemon:
        ``{"daemon": <name>, "pid": <PID> | null, "running": true | false,
        "restart_at": null | <timestamp>}``

   * ``{"command": "start", "daemon": <name>}`` -- start a daemon that
     is stopped or waits in backoff for restart

      * no data returned, just ``{"status": "ok"}``

   * ``{"command": "stop", "daemon": <name>}`` -- stop a daemon that is
     running or cancel its restart if it is waiting in backoff

      * no data returned, just ``{"status": "ok"}``

   * ``{"command": "restart", "daemon": <name>}`` -- restart running
     daemon (immediately if it waits in backoff) or start stopped one

      * no data returned, just ``{"status": "ok"}``

   * ``{"command": "cancel_restart", "daemon": <name>}`` -- cancel
     pending restart of a daemon. If daemon was running, nothing changes. If
     daemon was waiting in backoff timer, backoff is reset and the daemon is
     left stopped.

      * no data returned, just ``{"status": "ok"}``

Commands that operate on daemons (*start*, *stop*, *restart*,
*cancel_restart*) always reset backoff, even if nothing was changed (e.g.
stopping an already stopped daemon).


.. _specfile:

Daemon specifications file
==========================

Small overview on specfile:

.. code-block:: yaml

   defaults:
     environment:
       PYTHONPATH: lib

   daemons:
     streem:
       start_command: ...

Daemons in specfile are defined under hash called ``daemons``. Each daemon has
a name, by which it will be referred to in :ref:`commands <command-channel>`.

Daemon can have following variables:

   * ``start_command`` -- command used to start the daemon (can be a shell
     command, too)
   * ``stop_signal`` -- signal (number or name, like SIGTERM or TERM) to stop
     the daemon; defaults to *SIGTERM*
   * ``stop_command`` -- command used to stop running daemon; it will be
     executed with the same environment and working directory as
     ``start_command``; if both ``stop_signal`` and ``stop_command`` are
     defined, ``stop_command`` has the precedence
   * ``cwd`` -- working directory to start daemon in
   * ``environment`` -- additional environment variables to set (useful for
     setting :envvar:`$PYTHONPATH` or similar)
   * ``stdout`` -- what to do with daemon's *STDOUT* and *STDERR*

      * ``stdout`` or undefined -- pass the output to terminal
      * ``/dev/null`` -- redirect output to :file:`/dev/null`
      * ``log`` -- intercept *STDOUT*/*STDERR* and log it with :mod:`logging`
        module (**TODO**)

   * ``restart`` -- restart strategy; see :ref:`restart-strategy` for details

Default values for above-mentioned variables can be stored in ``defaults``
hash.

**NOTE**: ``environment`` key will be *replaced* by daemon's value, not
*merged*. It's not possible to add just one environment variable.

.. _restart-strategy:

Restart strategy
----------------

When a child dies, it's restarted after backoff time. If it dies again, next
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
:mod:`seismometer.daemonshepherd.controller.RestartQueue` module for
reference).

Example daemon spec file
------------------------

This is an example specification file that starts a set of tools to collect
monitoring data (``dumb-probe``), pass messages carrying state to another
channel (``state-forwarder``) and forward messages to
`collectd <http://collectd.org>`_ (``collectd-bridge``) and `WebASDB
<http://dozzie.jarowit.net/trac/wiki/WebASDB>`_ (``webasdb-bridge``):

.. code-block:: yaml

   defaults:
     # immediate, after 5s, after 10s, after 1 minute, try again each 5 minutes
     restart: [0, 5, 10, 60, 300]
     environment:
       PYTHONPATH: /usr/lib/seismometer/toolbox
     stdout: /dev/null

   daemons:
     streem:
       cwd: /var/lib/streem
       environment:
         ERL_LIBS: /usr/lib/streem
       start_command: "streem --control=/var/run/streem/control --bind=localhost:10101"
       stop_command: "streemctl --control=/var/run/streem/control stop"

     dumb-probe:
       start_command: "dumb-probe.py --destination=localhost:10101:probes --checks=/etc/seismometer/dumb_probe.py"

     state-forwarder:
       start_command: "pull-push-bridge.py --source=localhost:10101:probes --destination=localhost:10101:states --plugin=state_forwarder"

     webasdb-bridge:
       start_command: "pull-push-bridge.py --source=localhost:10101:states --destination=http://localhost/webasdb --plugin=webasdb"

     collectd-bridge:
       start_command: "pull-push-bridge.py --source=localhost:10101:probes --destination=/var/run/collectd.sock --plugin=collectd"
