#!/usr/bin/python
'''
Rate limiter for logging and other operations
---------------------------------------------

:class:`RateLimit` is useful for limiting number of consequent log entries,
connection retries and so on. It can also track custom information, like
number of messages dropped so far.

Small example of use::

   limit = RateLimit(dropped_messages = 0)
   # ...
   if is_dropped():
       limit.dropped_messages += 1
   if limit.dropped_messages > 0 and limit.should_fire():
       log.info("dropped: %d", limit.dropped_messages)
       limit.dropped_messages = 0
       limit.fired()

.. autoclass:: RateLimit
   :members:

'''
#-----------------------------------------------------------------------------

import time

#-----------------------------------------------------------------------------

class RateLimit:
    '''
    Rate limiter with some metadata storage.

    Limiter object can have custom values set, so it can track some additional
    data than merely when the operation was fired recently.
    '''
    def __init__(self, interval = 30, **kwargs):
        '''
        :param interval: minimum interval between operations
        :param kwargs: default values for additional fields
        '''
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

    def should_fire(self):
        '''
        :return: Boolean

        Check if the rate-limited operation should be fired now.
        '''
        return (self._last_event is None or \
                time.time() - self._last_event > self._interval)

    def fired(self):
        '''
        Mark the newest execution of the rate-limited operation.
        '''
        self.__dict__["_last_event"] = time.time()

    def reset(self):
        '''
        Reset the rate-limiting timer. Next :meth:`should_fire()` call will
        return ``True``.
        '''
        self.__dict__["_last_event"] = None

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
