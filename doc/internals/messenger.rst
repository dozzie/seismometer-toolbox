***************
*messenger* API
***************

Architecture
============

*messenger* prepares listening sockets, according to what was specified in
command line; then reads a message and sends it over to whatever was passed as
``--destination``. Any network problems with sending data are masked away from
data sender with on-disk or in-memory message spooling.

.. _messenger-api:

Modules
=======

Network input
-------------

.. automodule:: panopticon.messenger.net_input

.. automodule:: panopticon.messenger.net_input.stdin

.. automodule:: panopticon.messenger.net_input.inet

.. automodule:: panopticon.messenger.net_input.unix

Network output
--------------

.. automodule:: panopticon.messenger.net_output

.. automodule:: panopticon.messenger.net_output.stdout

.. automodule:: panopticon.messenger.net_output.inet

.. automodule:: panopticon.messenger.net_output.unix

Tag matcher
-----------

.. automodule:: panopticon.messenger.tags

Message spool
-------------

.. automodule:: panopticon.messenger.spool

