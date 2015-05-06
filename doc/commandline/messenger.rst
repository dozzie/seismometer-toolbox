***********
*messenger*
***********

*messenger* is a tool that receives messages for Seismometer and passes them
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

   Address to receive data on. ``<addr>`` can be in one of two forms:
   ``<host>:<port>`` (bind to ``<host>`` address) or ``<port>``.

   If no destination was provided, messages are printed to STDOUT.

.. cmdoption:: --destination stdout | tcp:<host>:<port> | udp:<host>:<port> | unix:<path>

   Address to send data to.

   If no destination was provided, messages are printed to STDOUT.

.. cmdoption:: --tagfile <pattern_file>

   File with patterns to convert tags to location and aspect name. See
   :ref:`messenger-tag-file`.

.. cmdoption:: --spool <directory>

   Spool directory. By default data is spooled in memory.

.. cmdoption:: --max-spool <size>

   Spool size. Affects on-disk and in-memory spooling.

.. cmdoption:: --logging <logging_config>

   Logging configuration file (YAML or JSON) with dictionary suitable for
   :func:`logging.config.dictConfig`. If not specified, messages (but only
   warnings) are printed to *STDERR*.

Signals
-------

*messenger* recognizes following signals:

* *SIGHUP* causes reloading tag pattern file
* *SIGTERM* causes termination

.. _messenger-protocol:

Communication protocol
----------------------

The protocol used by *messenger* encodes single message per line. Message can
be specified directly as JSON, in which case it's forwarded as-is, or be in
simplified, Graphite-like form (fields separated by at least one space or tab
character):

* ``tag value timestamp`` -- produces :class:`seismometer.message.Message`
  carrying a metric; *value* can be an integer, float, or a upper letter ``U``
  denoting undefined value
* ``tag state severity timestamp`` -- produces
  :class:`seismometer.message.Message` carrying a state; *state* is a single
  word (``/^[a-zA-Z0-9_]+$/``) and severity is one of the three words:
  ``expected``, ``warning``, ``critical``

Timestamp is expressed as epoch time (unix timestamp). Tag is a sequence of
words (``/^[a-zA-Z0-9_-]+$/``; dashes are allowed) separated by single period
(``"."``).

Tags are converted to location fields and aspect name according to
:ref:`pattern file <messenger-tag-file>`. Non-matching tags produce location
with field ``host`` filled with local hostname and aspect name filled with
whole tag.

.. _messenger-tag-file:

Tag pattern file
----------------

Pattern file contains patterns, according to which tags from Graphite-like
input are decomposed to location and aspect name for
:class:`seismometer.message.Message`.

Configuration file follows this grammar:

.. code-block:: none

   <line> :: <comment> | <pattern> | <definition>
   <comment> :: "#" *(any character)
   <pattern> :: <field-spec> *("." <field-spec>)
   <field-spec> :: <match-spec> ?(":" <field-name>)
   <match-spec> ::
       "(" <definition-name> ")"
     | "(*)"
     | "(**)"
     | <literal>
     | "[" <literal> *(<comma> <literal>) "]"
     | <regexp>
   <definition> :: <definition-name> "=" (<def-elem>) *(<comma> <def-elem>)
   <def-elem> :: <literal> | <regexp>
   <field-name> :: /^[a-zA-Z0-9_]+$/
   <literal> :: /^[a-zA-Z0-9_-]+$/
   <regexp> ::  "/" (regular expression) "/"
   <comma> :: /^[ \t,]+$/


Each statement can be broken into several lines by indenting the lines with
continuation. Spaces, except for the ones indenting and delimiting tokens, do
not matter.

Regular expressions, because of the *messenger*'s implementation, follow the
syntax of Python's :mod:`re` module. The only difference is that ``"/"``
character should be quoted by backslash, but given the tags cannot contain
slashes, it shouldn't matter.

There are two wildcard match specs: ``(*)`` and ``(**)``. The first one
matches exactly one field and can appear anywhere in the pattern. The latter
is called "slurp" and consumes all the remaining fields (minimum one), so
"slurp" has to be the last field match in the pattern.

Field names from the matching pattern tell which location fields should be
filled with what (obviously, if the field has no name, its content is not used
anywhere). An exception to this rule is field ``aspect``, which fills the
aspect name of :class:`seismometer.message.Message`.

**NOTE**: If the pattern does not specify ``host`` field, it will be filled
with hostname (``os.uname()[1]``). Similarly, ``aspect`` is filled with whole
tag unless defined by a field match. While ``host`` field is optional in
location and the limitation above will be addressed in the future, aspect name
is a required part of the message.

Example pattern file
^^^^^^^^^^^^^^^^^^^^

.. code-block:: none

   services = nginx collectd, fluentd, /d(aemon)?shepherd/,
              messenger

   /(..)lin(.)[1-4][0-9]/:host . (services):service . (**):aspect

   service . [nginx, httpd]:service . (*):aspect

   (services):service . (*):host . (*):aspect
