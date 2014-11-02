***********
*messenger*
***********

*messenger* is a tool that receives messages for Panopticon and passes them
over to another *messenger* or to Streem.

Usage
=====

.. code-block:: none

   messenger.py [--tagfile=<pattern_file>] [--source=<address> ...] [--destination=<address> ...]


*messenger* can also be used as a simple message converter:

.. code-block:: sh

   TAG=$(uname -n).uptime
   VALUE=$(cut -f1 -d' ' /proc/uptime)
   date +"$TAG $VALUE %s" | messenger.py

Command line options
--------------------

.. cmdoption:: --source stdin | tcp:<addr> | udp:<addr> | unix:<path>

   Destination to send data to. ``<addr>`` can be in one of two forms:
   ``<host>:<port>`` (bind to ``<host>`` address) or ``<port>``.

   If no destination was provided, messages are printed to STDOUT.

.. cmdoption:: --destination stdout | tcp:<host>:<port> | udp:<host>:<port> | unix:<path>

   Destination to send data to.

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
      * value: integer, float, ``U``
   * ``tag state severity timestamp``
      * severity: ``expected``, ``warning``, ``critical``

.. _messenger-tag-file:

Tag pattern file
----------------

**TODO**
