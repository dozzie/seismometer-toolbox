#!/usr/bin/python
'''
UNIX and TCP sockets
--------------------

.. autoclass:: ControlSocket
   :members:

.. autoclass:: ControlSocketClient
   :members:

'''
#-----------------------------------------------------------------------------

import socket
import os
import json

#-----------------------------------------------------------------------------

class ControlSocket:
    '''
    Create listening socket, binding to :obj:`address`. If it is a string,
    UNIX socket is created. For integer or tuple, TCP socket is used. With
    tuple, the socket is bound to IP address specified as the string part.
    '''

    def __init__(self, address):
        '''
        :param address: address to bind to
        :type address: string, integer or tuple (string, integer)
        '''
        # address = "path"
        # address = int(port)
        # address = (bindaddr, port)
        if isinstance(address, str): # UNIX
            self.path = os.path.abspath(address)
            self.socket = None
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            conn.bind(self.path)
            # only set self.socket it after bind(), so the file won't get
            # removed when it's not ours (e.g. existed already)
            self.socket = conn
        elif isinstance(address, int): # *:port
            self.path = None
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.bind(('', address))
        else:
            self.path = None
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.bind(address)
        self.socket.listen(1)

    def __del__(self):
        self.close()

    def accept(self):
        '''
        :rtype: :class:`ControlSocketClient`

        Accept new connection on this socket.
        '''
        (conn, addr) = self.socket.accept()
        return ControlSocketClient(conn)

    def fileno(self):
        '''
        Return file descriptor for this socket.

        Method intended for :func:`select.poll`.
        '''
        return self.socket.fileno()

    def close(self):
        '''
        Close the socket, possibly removing the file (UNIX socket).
        '''
        if self.socket is not None:
            self.socket.close()
            self.socket = None
            if self.path is not None:
                os.remove(self.path)

#-----------------------------------------------------------------------------

class ControlSocketClient:
    '''
    Client socket wrapper for line-based JSON communication.
    '''

    def __init__(self, socket):
        '''
        :param socket: connection to client
        '''
        self.socket = socket

    def read(self):
        '''
        :rtype: dict, list or scalar

        Read single line of JSON and decode it.
        '''
        line = self.socket.recv(4096)
        if line == '':
            return None
        try:
            result = json.loads(line)
            if isinstance(result, dict):
                return result
            else:
                return None
        except:
            return None

    def send(self, message):
        '''
        :param message: data structure to serialize as JSON and send to the
          client
        :type message: dict, list or scalar

        Send a JSON message to connected client.
        '''
        self.socket.send(json.dumps(message) + "\n")

    def fileno(self):
        '''
        Return file descriptor for this socket.

        Method intended for :func:`select.poll`.
        '''
        return self.socket.fileno()

    def close(self):
        '''
        Close the socket.
        '''
        if self.socket is not None:
            self.socket.close()
            self.socket = None

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
