#!/usr/bin/python
'''
Unix sockets
------------

.. autoclass:: ControlSocket
   :members:

.. autoclass:: ControlSocketClient
   :members:

'''
#-----------------------------------------------------------------------------

import socket
import os
import errno
import json
import filehandle

#-----------------------------------------------------------------------------

class ControlSocket:
    '''
    Create unix stream listening socket, binding to :obj:`address`.
    '''

    def __init__(self, address):
        '''
        :param address: address to bind to
        :type address: string
        '''
        self.path = os.path.abspath(address)
        self.socket = None
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.bind(self.path)
        # only set self.socket it after bind(), so the file won't get removed
        # when it's not ours (e.g. existed already)
        self.socket = conn
        filehandle.set_close_on_exec(self.socket)
        self.socket.listen(1)

    def __del__(self):
        self.close()

    def accept(self):
        '''
        :rtype: :class:`ControlSocketClient`

        Accept new connection on this socket.
        '''
        (conn, addr) = self.socket.accept()
        filehandle.set_close_on_exec(conn)
        return ControlSocketClient(conn)

    def fileno(self):
        '''
        Return file descriptor for this socket.

        Method intended for :func:`select.poll`.
        '''
        return self.socket.fileno()

    def close(self):
        '''
        Close the socket, possibly removing the file (unix socket).
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

        This method is non-blocking; if no more data is ready for reading, the
        method returns immediately ``None``.

        When connection was closed, this method returns
        :obj:`seismometer.daemonshepherd.filehandle.EOF`.
        '''
        if self.socket is None:
            return filehandle.EOF
        try:
            line = self.socket.recv(4096, socket.MSG_DONTWAIT)
        except socket.error, e:
            if e.errno == errno.EWOULDBLOCK or e.errno == errno.EAGAIN:
                # nothing more to read at the moment
                return None
            else:
                raise

        if line == '':
            return filehandle.EOF
        try:
            result = json.loads(line)
            if isinstance(result, dict):
                return result
            else:
                return filehandle.EOF # TODO: report a protocol error
        except:
            return filehandle.EOF # TODO: report a protocol error

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
