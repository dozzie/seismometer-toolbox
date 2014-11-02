#!/usr/bin/python
'''
Generic 

.. autoclass:: ConnectionOutput
   :members:

'''
#-----------------------------------------------------------------------------

import json
import panopticon.messenger.spool

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
      (defaults to :class:`panopticon.messenger.spool.MemorySpooler` instance)
    '''
    if spooler is None:
      self.spooler = panopticon.messenger.spool.MemorySpooler()
    else:
      self.spooler = spooler

  def write(self, line):
    '''
    :return: ``True`` when line was sent successfully, ``False`` when problems
      occurred

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

    Try connecting to the remote side. Function to be implemented in subclass.
    '''
    raise NotImplementedError()

  def send(self, message):
    '''
    :param message: message to send

    Send single message.

    In case of connectivity errors message will be spooled and sent later.
    '''
    line = json.dumps(message) + "\n"

    if not self.is_connected() and not self.repair_connection():
      # lost connection, can't repair it at the moment
      self.spooler.spool(line)
      return

    # self.is_connected()
    if not self.send_pending() or not self.write(line):
      # didn't send all the pending lines -- make the current one pending, too
      # didn't send the current line -- make it pending
      self.spooler.spool(line)

  def send_pending(self):
    '''
    :return: ``True`` if all pending messages were sent successfully,
      ``False`` otherwise.

    Send all pending messages.
    '''
    line = self.spooler.peek()
    while line is not None:
      if self.write(line):
        self.spooler.drop_one()
        line = self.spooler.peek()
      else:
        return False
    return True

  def flush(self):
    '''
    Flush spool.
    '''
    if not self.is_connected() and not self.repair_connection():
      return
    self.send_pending()

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
