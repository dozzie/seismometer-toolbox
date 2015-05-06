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
import logging
import seismometer.logging.rate_limit
import platform

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
        # "connection still closed" rate limiter
        self.conn_still_closed = seismometer.logging.rate_limit.RateLimit()
        super(TCP, self).__init__(spooler)

    def get_logger(self):
        return logging.getLogger("output.tcp")

    def get_name(self):
        return "%s:%d" % (self.host, self.port)

    def write(self, line):
        if self.conn is None:
            return False

        try:
            self.conn.send(line)
            return True
        except socket.error: # this covers `socket.timeout'
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
            conn = socket.socket()
            conn.settimeout(5) # 5s timeout for connect, send, and such
            conn.connect((self.host, self.port))
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if platform.system() == "Linux":
                # XXX: unportable, Linux-specific code
                # send first probe after 30s
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                # keep sending probes every 30s
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)
                # after this many probes the connection drops
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 9)
            self.conn = conn
            logger.info("%s: reconnected", self.get_name())
            self.conn_still_closed.reset()
            return True
        except socket.timeout, e:
            if self.conn_still_closed.should_log():
                logger.warn("%s: reconnecting failed: timeout", self.get_name())
                self.conn_still_closed.logged()
            return False
        except socket.error, e:
            if self.conn_still_closed.should_log():
                logger.warn("%s: reconnecting failed: %s", self.get_name(),
                            e.strerror)
                self.conn_still_closed.logged()
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
