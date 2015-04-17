#!/usr/bin/python
'''
Network output sockets.

.. autoclass:: TCP
   :members:

.. autoclass:: UDP
   :members:

'''
#-----------------------------------------------------------------------------

import socket
import json
from _connection_output import ConnectionOutput

#-----------------------------------------------------------------------------

class TCP(ConnectionOutput):
    '''
    Sender passing message to another messenger (or anything accepting raw JSON
    lines through TCP).
    '''
    def __init__(self, host, port, spooler = None):
        '''
        :param host: address to send data to
        :param port: address to send data to
        :param spooler: spooler object
        '''
        self.host = host
        self.port = port
        self.conn = None
        super(TCP, self).__init__(spooler)

    def write(self, line):
        if self.conn is None:
            return False

        try:
            self.conn.send(line)
            return True
        except socket.error:
            # lost connection
            self.conn = None
            return False

    def is_connected(self):
        # FIXME: better check
        return (self.conn is not None)

    def repair_connection(self):
        try:
            conn = socket.socket()
            conn.connect((self.host, self.port))
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.conn = conn
            return True
        except socket.error:
            return False

#-----------------------------------------------------------------------------

class UDP:
    '''
    Sender passing message to another messenger (or anything accepting raw JSON
    lines through UDP).
    '''

    def __init__(self, host, port):
        '''
        :param host: address to send data to
        :param port: address to send data to
        '''
        self.host = host
        self.port = port
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.conn.connect((self.host, self.port))

    def send(self, message):
        line = json.dumps(message) + "\n"
        self.conn.send(line)

    def flush(self):
        pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
