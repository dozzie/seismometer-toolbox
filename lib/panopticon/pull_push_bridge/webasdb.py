#!/usr/bin/python

import httplib
import urlparse
import json

#-----------------------------------------------------------------------------
# WebASDB client class {{{

class WebASDBSubmit:
  class ProtocolError(Exception):
    pass

  def __init__(self, base_url):
    self.base_url = base_url

    parsed = urlparse.urlparse(base_url)
    self.hostname = parsed.hostname
    if parsed.port is not None:
      self.port = parsed.port
    elif parsed.scheme == 'http':
      self.port = 80
    elif parsed.scheme == 'https':
      self.port = 443
    self.base_path = parsed.path
    self.post_path = "%s/api" % (self.base_path.rstrip('/'),)

    self.conn = httplib.HTTPConnection(self.hostname, self.port)

  def submit(self, resource, status, severity = "ok",
                   time = None, expire_time = None, expire_after = None,
                   body = None):
    from time import time as now

    if time is None:
      time = int(now())

    message = {
      'resource': resource,
      'status':   status,
      'severity': severity,
      'time':     time,
      'body':     body,
    }
    if expire_time is not None:
      message['expire_time'] = expire_time
    elif expire_after is not None:
      message['expire_after'] = expire_after

    self.conn.request('POST', self.post_path + '/', json.dumps(message) + '\n')
    response = self.conn.getresponse()
    response_body = response.read()
    if response.status / 100 == 5:
      raise WebASDBSubmit.ProtocolError(
        "server error %s: %s" % (response.status, response.reason)
      )
    if response.status / 100 == 4:
      raise WebASDBSubmit.ProtocolError(
        "request error %s: %s" % (response.status, response.reason)
      )
    if response.status / 100 == 3:
      raise WebASDBSubmit.ProtocolError(
        "unexpected redirect %s: %s" % (response.status, response.reason)
      )
    message_id = response_body.strip()
    return message_id

  # XXX: this method won't be necessary in this plugin
  def get(self, message_id):
    url = "%s/status/%s" % (self.post_path, message_id)
    self.conn.request('GET', url)
    response = self.conn.getresponse()
    result = response.read()
    if response.status / 100 == 2:
      return json.loads(result)
    else:
      # TODO: raise error on 4xx/5xx
      return None

  # XXX: this method won't be necessary in this plugin
  def delete(self, message_id):
    url = "%s/status/%s" % (self.post_path, message_id)
    self.conn.request('DELETE', url)
    response = self.conn.getresponse()
    response.read() # ignore output

# }}}
#-----------------------------------------------------------------------------

class PullPushBridge:
  def __init__(self, options):
    self.url = options.destination
    self.webasdb = WebASDBSubmit(self.url)

  def send(self, message):
    try:
      # FIXME: hardcoded for ModMon::Event v=1
      if (message.get('v') == 1) and 'value' in message['event']['state']:
        status = message['event']['state']['value']
        states_ok   = message['event']['state'].get('expected', ['ok'])
        states_warn = message['event']['state'].get('attention', [])
        if status in states_ok:
          severity = 'ok'
        elif status in states_warn:
          severity = 'warning'
        else:
          severity = 'error'

        resource = message['location'].copy()
        resource['aspect'] = message['event']['name']

        self.webasdb.submit(
          resource = resource,
          status   = status,
          severity = severity,
          time = message['time'],
          body = message,
        )
    except KeyError:
      pass
    except WebASDBSubmit.ProtocolError:
      # assume it's a temporary error
      # FIXME: this is generally not a good idea to skip this silently
      pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
