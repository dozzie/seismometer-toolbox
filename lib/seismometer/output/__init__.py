#!/usr/bin/python
'''
Sending a message to bunch of output sockets
--------------------------------------------

Output sockets are only expected to implement ``send()`` and ``flush()``
methods.

* ``send(message)`` will be called with a dictionary representing a message
  for every message to send (``message`` serializes clearly to JSON)
* ``flush()`` will be called in regular intervals, to give output sockets the
  chance to repair connection and send pending messages

Connectivity problems are not handled at :class:`Writer` level. It is assumed
that the socket spools messages in case of errors.

Example implementation of output socket that ignores all the messages::

   class NullOutput:
       def send(self, message):
           pass
       def flush(self):
           pass

.. autoclass:: Writer
   :members:

'''
#-----------------------------------------------------------------------------

import json
import signal

import inet, stdout, unix
__all__ = [
    'Writer',
    'inet', 'stdin', 'unix',
]

#-----------------------------------------------------------------------------

class Writer:
    '''
    Write a message to all added output sockets at once.
    '''
    def __init__(self):
        self.outputs = []

        # setup SIGALRM to be called every N seconds and try flushing all the
        # outputs (reconnecting to the remote if necessary)
        flush_interval = 10
        def alarm_handler(sig, stack):
            for o in self.outputs:
                o.flush()
            signal.alarm(flush_interval)
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(flush_interval)

    def add(self, output):
        '''
        :param output: output socket to add

        Add output socket to the list.
        '''
        self.outputs.append(output)

    def write(self, message):
        for o in self.outputs:
            o.send(message)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
