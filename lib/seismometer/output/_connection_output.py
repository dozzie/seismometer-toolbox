#!/usr/bin/python
'''
Generic 

.. autoclass:: ConnectionOutput
   :members:

'''
#-----------------------------------------------------------------------------

import json
import seismometer.spool
import seismometer.rate_limit

#-----------------------------------------------------------------------------

class ConnectionOutput(object):
    '''
    Base class for output sockets that use *CONNECT* operation of some sort
    (e.g. TCP, stream/datagram UNIX sockets), which spools messages in case of
    connectivity problems.
    '''

    def __init__(self, spooler = None):
        '''
        :param spooler: place to put messages in case of connectivity problems
            (defaults to :class:`seismometer.messenger.spool.MemorySpooler`
            instance)
        '''
        if spooler is None:
            self.spooler = seismometer.spool.MemorySpooler()
        else:
            self.spooler = spooler
        self.spool_dropped = seismometer.rate_limit.RateLimit(count = 0)

    def __del__(self):
        logger = self.get_logger()
        if self.spool_dropped.count > 0:
            logger.warn("%s: dropped %d pending messages", self.get_name(),
                        self.spool_dropped.count)
        logger.info("%s: %d messages left in queue", self.get_name(),
                    len(self.spooler))

    def write(self, line):
        '''
        :return: ``True`` when line was sent successfully, ``False`` when
            problems occurred

        Write a single line to socket. Function to be implemented in subclass.
        '''
        raise NotImplementedError()

    def is_connected(self):
        '''
        Check if the object has connection to the remote side. Function to be
        implemented in subclass.
        '''
        raise NotImplementedError()

    def repair_connection(self):
        '''
        :return: ``True`` if connected successfully, ``False`` otherwise.

        Try connecting to the remote side. Function to be implemented in
        subclass.
        '''
        raise NotImplementedError()

    def get_logger(self):
        '''
        :return: logger instance (see :mod:`logging` module)
        '''
        raise NotImplementedError()

    def get_name(self):
        '''
        :return: string identifying output

        Return a human-meaningful string representation of the output
        (typically: target address) for logging.
        '''
        raise NotImplementedError()

    def send(self, message):
        '''
        :param message: message to send

        Send single message.

        In case of connectivity errors message will be spooled and sent later.
        '''
        line = json.dumps(message) + "\n"
        logger = self.get_logger()

        if not self.is_connected() and not self.repair_connection():
            # lost connection, can't repair it at the moment
            dropped_count = self.spooler.spool(line)
            self.spool_dropped.count += dropped_count
            if self.spool_dropped.count > 0 and \
               self.spool_dropped.should_fire():
                logger.warn("%s: dropped %d pending messages", self.get_name(),
                            self.spool_dropped.count)
                self.spool_dropped.count = 0
                self.spool_dropped.fired()
            return

        # self.is_connected()
        if self.spool_dropped.count > 0:
            logger.warn("%s: dropped %d pending messages", self.get_name(),
                        self.spool_dropped.count)
            self.spool_dropped.count = 0
            self.spool_dropped.reset()

        if not self.send_pending() or not self.write(line):
            # didn't send all the pending lines -- make the current one
            # pending, too didn't send the current line -- make it pending
            dropped_count = self.spooler.spool(line)
            self.spool_dropped.count += dropped_count
            if self.spool_dropped.count > 0 and \
               self.spool_dropped.should_fire():
                logger.warn("%s: dropped %d pending messages", self.get_name(),
                            self.spool_dropped.count)
                self.spool_dropped.count = 0
                self.spool_dropped.fired()

    def send_pending(self):
        '''
        :return: ``True`` if all pending messages were sent successfully,
            ``False`` otherwise.

        Send all pending messages.
        '''
        pending_before = len(self.spooler)

        sent_all_pending = True
        line = self.spooler.peek()
        while line is not None:
            if self.write(line):
                self.spooler.drop_one()
                line = self.spooler.peek()
            else:
                sent_all_pending = False
                break

        pending_after = len(self.spooler)
        if pending_before != pending_after:
            # no need to log totally unsuccessful flushes (partially
            # successful ones are somewhat interesting, however)
            logger = self.get_logger()
            logger.info("%s: sent %d pending messages, %d left",
                        self.get_name(), pending_before - pending_after,
                        pending_after)
        return sent_all_pending

    def flush(self):
        '''
        Flush spool.
        '''
        if not self.is_connected() and not self.repair_connection():
            return
        self.send_pending()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
