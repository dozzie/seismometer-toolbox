**************************
*daemonshepherd* internals
**************************

Architecture
============

**TODO**


Top-level operations
====================

.. automodule:: seismometer.daemonshepherd


Daemonizing *daemonshepherd*
============================

.. automodule:: seismometer.daemonshepherd.self_detach

.. automodule:: seismometer.daemonshepherd.setguid

.. automodule:: seismometer.daemonshepherd.pid_file


Controlling child processes
===========================

.. automodule:: seismometer.daemonshepherd.controller

.. automodule:: seismometer.daemonshepherd.control_socket

.. automodule:: seismometer.daemonshepherd.daemon

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

