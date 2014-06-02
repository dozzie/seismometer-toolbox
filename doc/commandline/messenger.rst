***********
*messenger*
***********

*messenger* is a tool that receives messages for Panopticon and passes them
over to another *messenger* or to Streem.

Usage
=====

.. code-block:: none

   messenger.py [--tagfile=<pattern_file>] [--destination=<address>] <listen_spec>

*messenger* can also be used as a simple message converter:

.. code-block:: sh

   TAG=$(uname -n).uptime
   VALUE=$(cut -f1 -d' ' /proc/uptime)
   date +"$TAG $VALUE %s" | messenger.py -

Command line options
--------------------

.. cmdoption:: --destination <host>:<port> | <host>:<port>:<channel>

   Destination to send data to. In the form ``<host>:<port>``, simple
   TCP protocol is used (one JSON document per line, no confirmations). In the
   form ``<host>:<port>:<channel>``, Streem's SJCP protocol is used.

   If no destination was provided, messages are printed to STDOUT.

.. cmdoption:: --tagfile <pattern_file>

   File with patterns to convert tags to location and aspect name. See
   :ref:`messenger-tag-file`.

.. cmdoption:: --spool <directory>

   Spool directory. By default data is spooled in memory.

.. cmdoption:: --max-spool <size>

   Spool size. Affects on-disk and in-memory spooling.

.. _messenger-protocol:

Communication protocol
----------------------

**TODO**: describe this in more detail

* linewise protocol
   * JSON hash
   * ``tag value timestamp``
   * ``tag state severity timestamp``

.. _messenger-tag-file:

Tag pattern file
----------------

**TODO**
