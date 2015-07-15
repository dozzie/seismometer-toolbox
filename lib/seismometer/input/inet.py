#!/usr/bin/python
'''
Network sockets: TCP and UDP
----------------------------

.. autoclass:: TCP
   :members:

.. autoclass:: TCPConnection
   :members:

.. autoclass:: UDP
   :members:

'''
#-----------------------------------------------------------------------------

import sys
import os
import socket
import seismometer.poll
import seismometer.message
import Queue
import json

from _connection_socket import ConnectionSocket

#-----------------------------------------------------------------------------

# NOTE: this class is intended for use when add() call is followed by
# has_lines() (and by get_lines(), if has_lines() returned True)
class LineBuffer:
    def __init__(self, max = 16 * 1024):
        self._buffer = []
        #self._size = 0
        #self._max = max

    def add(self, chunk):
        # TODO: check size
        self._buffer.append(chunk)

    def has_lines(self):
        return len(self._buffer) > 0 and '\n' in self._buffer[-1]

    def get_lines(self):
        # return all the lines up until last NL; stuff after last NL is an
        # unfinished line, so it forms 
        everything = ''.join(self._buffer)
        (lines, tail) = everything.rsplit('\n', 1)
        del self._buffer[:]
        if tail != '':
            self.add(tail)
        return lines

#-----------------------------------------------------------------------------

class TCP(ConnectionSocket):
    '''
    Listening TCP socket. Not intended for reading itself, instead returns
    connection objects.
    '''
    def __init__(self, host, port):
        '''
        :param host: bind address
        :type host: string or ``None``
        :param port: bind address
        :type port: integer
        '''
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if host is not None:
            self.conn.bind((host, port))
        else:
            self.conn.bind(('', port))
        self.conn.listen(256)

    def accept(self):
        '''
        :rtype: :class:`TCPConnection`

        Accept a connection.
        '''
        (client, (host, port)) = self.conn.accept()
        client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        return TCPConnection(client, host)

    def fileno(self):
        return self.conn.fileno()

class TCPConnection:
    '''
    TCP connection reader.

    Instances of this class are created by :class:`TCP`.
    '''
    def __init__(self, conn, host):
        '''
        :param conn: connection descriptor
        :type conn: socket.socket()
        :param host: remote end address
        :type host: string
        '''
        self.conn = conn
        # TODO: resolve hostname (some cache maybe?)
        self.host = host
        self._buffer = LineBuffer()

    def __del__(self):
        self.close()

    def close(self):
        '''
        Close TCP connection.
        '''
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def readline(self):
        '''
        :return: ``(host, string)``

        Read complete line (or lines) from the connection.
        '''
        line = self.conn.recv(16384)
        if line == '':
            return (None, None)

        self._buffer.add(line)
        if self._buffer.has_lines():
            return (self.host, self._buffer.get_lines())
        else:
            # tell the caller it's not EOF, but nothing interesting was read
            return (self.host, '')

    def fileno(self):
        '''
        Return file descriptor for ``poll()``
        '''
        return self.conn.fileno()

#-----------------------------------------------------------------------------

class UDP:
    '''
    Listening UDP socket.
    '''
    def __init__(self, host, port):
        '''
        :param host: bind address
        :type host: string or ``None``
        :param port: bind address
        :type port: integer
        '''
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if host is not None:
            self.conn.bind((host, port))
        else:
            self.conn.bind(('', port))

    def readline(self):
        '''
        :return: ``(host, string)``

        Read a single line sent to this port.
        '''
        # XXX: no EOF is expected here
        (line, (host, port)) = self.conn.recvfrom(16384)
        # TODO: resolve hostname (some cache maybe?)
        return (host, line.strip())

    def fileno(self):
        '''
        Return file descriptor for ``poll()``
        '''
        return self.conn.fileno()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
