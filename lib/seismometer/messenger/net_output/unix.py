#!/usr/bin/python
'''
UNIX domain socket writer.

.. autoclass:: UNIX
   :members:

'''
#-----------------------------------------------------------------------------

import os
import socket
import logging
import seismometer.logging.rate_limit
from _connection_output import ConnectionOutput

#-----------------------------------------------------------------------------

class UNIX(ConnectionOutput):
    '''
    Sender passing message to another messenger through UNIX sockets.
    '''
    def __init__(self, path, spooler = None):
        '''
        :param path: socket path to send data to
        :param spooler: spooler object
        '''
        self.path = os.path.abspath(path)
        self.conn = None
        # "connection still closed" rate limiter
        self.conn_still_closed = seismometer.logging.rate_limit.RateLimit()
        super(UNIX, self).__init__(spooler)

    def get_logger(self):
        return logging.getLogger("output.af_unix")

    def get_name(self):
        return "%s" % (self.path,)

    def write(self, line):
        if self.conn is None:
            return False

        try:
            self.conn.send(line)
            return True
        except socket.error:
            # lost connection
            logger = self.get_logger()
            logger.warn("%s: lost connection", self.get_name())
            self.conn = None
            return False

    def is_connected(self):
        # FIXME: better check
        return (self.conn is not None)

    def repair_connection(self):
        logger = self.get_logger()
        try:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            conn.connect(self.path)
            self.conn = conn
            logger.info("%s: reconnected", self.get_name())
            self.conn_still_closed.reset()
            return True
        except socket.error, e:
            if self.conn_still_closed.should_log():
                logger.warn("%s: reconnecting failed: %s", self.get_name(),
                            e.strerror)
                self.conn_still_closed.logged()
            return False

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
