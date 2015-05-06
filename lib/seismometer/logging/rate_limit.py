#!/usr/bin/python

import time

#-----------------------------------------------------------------------------

class RateLimit:
    def __init__(self, interval = 30, **kwargs):
        self.__dict__["_fields"] = kwargs
        self.__dict__["_interval"] = interval
        self.__dict__["_last_event"] = None

    def __getattr__(self, name):
        if name not in self._fields:
            raise AttributeError("no such field: %s" % (name,))
        return self._fields[name]

    def __setattr__(self, name, value):
        self.__dict__["_fields"][name] = value

    def __delattr__(self, name):
        if name in self._fields:
            del self._fields[name]

    def should_log(self):
        return (self._last_event is None or \
                time.time() - self._last_event > self._interval)

    def logged(self):
        self.__dict__["_last_event"] = time.time()

    def reset(self):
        self.__dict__["_last_event"] = None

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
