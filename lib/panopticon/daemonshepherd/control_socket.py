#!/usr/bin/python

import socket
import os
import json

#-----------------------------------------------------------------------------

class ControlSocket:
  def __init__(self, address):
    # address = "path"
    # address = int(port)
    # address = (bindaddr, port)
    if isinstance(address, str): # UNIX
      self.path = os.path.abspath(address)
      self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      self.socket.bind(self.path)
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
    (conn, addr) = self.socket.accept()
    return ControlSocketClient(conn)

  def fileno(self):
    return self.socket.fileno()

  def close(self):
    if self.socket is not None:
      self.socket.close()
      self.socket = None
      if self.path is not None:
        os.remove(self.path)

#-----------------------------------------------------------------------------

class ControlSocketClient:
  def __init__(self, socket):
    self.socket = socket

  def read(self):
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

  def send(self, reply):
    self.socket.send(json.dumps(reply) + "\n")

  def fileno(self):
    return self.socket.fileno()

  def close(self):
    if self.socket is not None:
      self.socket.close()
      self.socket = None

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
