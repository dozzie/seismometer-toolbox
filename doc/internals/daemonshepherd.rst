**************************
*daemonshepherd* internals
**************************

Architecture
============

The central part of *daemonshepherd* is daemons controller object, an instance
of :class:`seismometer.daemonshepherd.controller.Controller`. This object runs
the main event loop (:meth:`Controller.loop()
<seismometer.daemonshepherd.controller.Controller.loop()>`), which starts the
daemons, restarts them on their termination, polls daemons' *STDOUT* and
*STDERR* to log it, polls control socket (if any) and executes commands
received on it.

Controller object keeps daemons' handles, restart queue, poll object for
filehandles (daemons' outputs and control socket connections), and config
loader callback function. Controller also sets up handlers for signals
(*SIGCHLD*, *SIGHUP*, *SIGINT*, *SIGTERM*).

Restart queue (:class:`seismometer.daemonshepherd.controller.RestartQueue`)
tracks the state of the daemons (*started*, *stopped*, *died*), their restart
strategy, and decides when to restart each one that died (the queue contains
an algorithm for increasing restart backoff).

Daemon handle (:class:`seismometer.daemonshepherd.daemon.Daemon`) carries
information about how to start and stop daemon (including its initial working
directory, environment, user and group to run as, and so on), remembers PID of
a running process and reading end of process' *STDOUT*/*STDERR*. Comparing two
daemon handles with ``==`` and ``!=`` operators tells whether the
*definitions* are the same. This allows to tell which daemons to restart when
reloading config.

Daemon handle can also remember arbitrary metadata that doesn't strictly
belong to the handle, like restart strategy or start priority.

Control socket
(:class:`seismometer.daemonshepherd.control_socket.ControlSocket` and
:class:`seismometer.daemonshepherd.control_socket.ControlSocketClient`) is
a unix socket that is removed from disk when closed. Reading/writing
automatically converts messages from/to JSON lines. Messages that come through
a control socket connection are treated by the controller object as
administrative commands. For details about the protocol, see
:ref:`daemonshepherd-control-channel`.

Daemonizing *daemonshepherd*
============================

.. automodule:: seismometer.daemonshepherd.self_detach

.. automodule:: seismometer.daemonshepherd.setguid

.. automodule:: seismometer.daemonshepherd.pid_file


Controlling child processes
===========================

.. automodule:: seismometer.daemonshepherd.controller

.. automodule:: seismometer.daemonshepherd.control_socket

.. automodule:: seismometer.daemonshepherd.filehandle

.. automodule:: seismometer.daemonshepherd.daemon

.. _daemonshepherd-control-channel:

Administrative control channel
==============================

*daemonshepherd* allows to control its supervised daemons through a unix
socket. The protocol used for communication is a synchronous exchange of JSON
documents, each in its own line.

Requests closely resemble what ``daemonshepherd`` command allows (see
:ref:`daemonshepherd-commands`). Command name is specified as ``command`` key,
and arguments, if any, are passed as keys along with ``command``.

Response is a document ``{"status": "ok"}`` or
``{"status": "ok", "result": ...}``, depending on the command called. Errors
are signaled with ``{"status": "error", "reason": "..."}``.

Available requests
------------------

* ``{"command": "reload"}`` -- reload daemons definition file

  * no data returned, just ``{"status": "ok"}``

* ``{"command": "ps"}`` -- list daemons names (all that were defined in
  configuration, currently running ones and the ones with restart pending)

  * response result:
    ``{"result": [<info1>, <info2>, ...], "status": "ok"}``
  * ``<infoX>`` is a hash containing information about the daemon:
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

* ``{"command": "admin_command", "daemon": <name>, "admin_command":
  <command>}`` -- run an administrative command according to daemon's
  definition

  * no data returned, just ``{"status": "ok"}``

Commands that operate on daemons (*start*, *stop*, *restart*,
*cancel_restart*) always reset backoff, even if nothing was changed (e.g.
stopping an already stopped daemon).

