#!/usr/bin/python
'''
UNIX domain sockets.

.. autoclass:: UNIX
   :members:

'''
#-----------------------------------------------------------------------------

import os
import socket

#-----------------------------------------------------------------------------

class UNIX:
    '''
    Listening UNIX datagram socket.
    '''
    def __init__(self, path):
        '''
        :param path: socket address
        :type path: string
        '''
        self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.conn.bind(path)
        self.path = os.path.abspath(path)

    def __del__(self):
        self.conn.close()
        os.unlink(self.path)

    def readline(self):
        # XXX: no EOF is expected here
        line = self.conn.recv(16384)
        return (None, line.strip())

    def fileno(self):
        return self.conn.fileno()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
