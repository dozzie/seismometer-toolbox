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

Network output
--------------

.. automodule:: panopticon.messenger.net_output

Tag matcher
-----------

.. automodule:: panopticon.messenger.tags

Message spool
-------------

.. automodule:: panopticon.messenger.spool

