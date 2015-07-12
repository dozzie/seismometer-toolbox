#!/usr/bin/python
'''
Reading from a bunch of input sockets
-------------------------------------

.. autoclass:: Reader
   :members:

.. autoclass:: JSONReader
   :members:

.. autoexception:: EOF
   :members:

'''
#-----------------------------------------------------------------------------

import seismometer.poll
import Queue
import json

from _connection_socket import ConnectionSocket

import inet, stdin, unix
__all__ = [
    'EOF', 'Reader', 'JSONReader',
    'inet', 'stdin', 'unix',
]

#-----------------------------------------------------------------------------

class EOF(Exception):
    '''
    EOF condition on all the inputs.
    '''
    pass

#-----------------------------------------------------------------------------

class ReadQueue:
    '''
    Read a line from any polled socket.
    '''
    def __init__(self):
        self.poll = seismometer.poll.Poll()
        self.queue = Queue.Queue()

    def add(self, sock):
        '''
        Add new socket to poll list.
        '''
        self.poll.add(sock)

    def remove(self, sock):
        '''
        Remove socket from poll list.

        Raises :class:`EOF` when there is no more sockets to read from after
        this function finishes.
        '''
        self.poll.remove(sock)
        if self.poll.empty():
            raise EOF()

    def readline(self):
        '''
        :return: originating host and line received
        :rtype: tuple (string, string)

        Read single line from all the sockets from poll list.

        Raises :class:`EOF` when there is no more sockets to read from.
        '''
        # XXX: in any given poll there could be just TCP connection attempts and
        # closed sockets with no incoming data
        while self.queue.empty():
            for sock in self.poll.poll(-1): # wait for any input
                if isinstance(sock, ConnectionSocket):
                    # connection attempt, add client to poll and skip reading
                    client = sock.accept()
                    self.add(client)
                    continue

                (host, line) = sock.readline()
                if line is None:
                    # EOF, remove the socket from poll
                    self.remove(sock)
                elif line == '':
                    # no data read, but not EOF yet (maybe partial line)
                    pass
                else:
                    # some data (maybe multiline)
                    for l in line.split('\n'):
                        self.queue.put((host, l.strip()))

        # loop ended, so there must be anything in the queue
        return self.queue.get()

#-----------------------------------------------------------------------------

class Reader(object):
    '''
    Network reader, polling for a line and converting it to proper message.

    This is a base class for different line-based protocols. See
    :class:`JSONReader` for an example implementation.
    '''
    def __init__(self):
        self.poll = ReadQueue()

    def add(self, sock):
        '''
        Add a socket to poll list.
        '''
        self.poll.add(sock)

    def read(self):
        '''
        :rtype: dict

        Read a message from polled sockets.

        Raises :class:`EOF` when there is no more sockets to read from.
        '''
        # try reading and parsing until a good message is produced
        while True:
            (host, line) = self.poll.readline()
            message = self.parse_line(host, line)

            if message is not None:
                return message

            # else (message is None): try reading next message

    def parse_line(self, host, line):
        '''
        :param host: name of the host that sent the message
        :param line: serialized message sent from the host

        Parse line to a usable message. Method should return ``None`` if
        nothing could be parsed.

        Method to be implemented in subclass.
        '''
        raise NotImplementedError("parse_line() not implemented")

class JSONReader(Reader):
    '''
    Network reader, expecting JSON object per line.
    '''
    def parse_line(self, host, line):
        if line == '':
            return None

        if line[0] == '{': # JSON
            try:
                return json.loads(line)
            except ValueError:
                return None
        return None

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
