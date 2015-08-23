#!/usr/bin/python
'''
Messages are expected to conform to `message schema
<http://seismometer.net/message-schema/v3>`_.

.. autodata:: SCHEMA_VERSION

.. autofunction:: is_valid()

Message class
-------------

.. autoclass:: Message
   :members:
   :member-order: groupwise

Auxiliary classes
-----------------

These classes represent specific data inside of :class:`Message`.

.. autoclass:: Value
   :members:
   :member-order: groupwise

.. autoclass:: Location
   :members:

'''
#-----------------------------------------------------------------------------

from time import time as now

#-----------------------------------------------------------------------------

SCHEMA_VERSION = 3
'''
Version of schema this module supports. Equals to ``3``, meaning the module
supports  `message schema v3 <http://seismometer.net/message-schema/v3>`_.
'''

# guard for saying that "value" is not specified, so `None' can work as
# null
_NOTHING = "NOT_SPECIFIED"

#-----------------------------------------------------------------------------

class Value(object):
    '''
    Value representation for Seismometer message.

    :class:`Value` instance is convertible to integer and float
    (``int(v)``) if it doesn't represent ``None``.

    :class:`Value` instance is comparable (e.g. ``<=`` or ``==``) with
    numerics, other :class:`Value` instances and with ``None``. ``None`` is
    always smaller than any numeric.
    '''
    def __init__(self, value, name = None, unit = None, type = None):
        '''
        :param value: value
        :param name: name of the value
        :type value: integer, float or ``None``
        :param unit: unit of measurement
        :param type: type of change of the value
        :type type: ``"direct"``, ``"accumulative"`` or ``"differential"``
        '''
        self._name = name
        self.value = value
        self.unit = unit
        self.type = type
        self._threshold_low = {}
        self._threshold_high = {}

    def copy(self):
        '''
        Deep copy of the instance.
        '''
        result = Value(
            self.name,
            self.value,
            self.unit,
            self.type,
        )
        result._threshold_low  = self._threshold_low.copy()
        result._threshold_high = self._threshold_high.copy()
        return result

    def __repr__(self):
        return "<Value %s=%s>" % (self.name, self.value)

    def to_dict(self):
        '''
        Dictionary representing the value.
        '''
        result = {
            "value": self.value,
        }
        if self.unit is not None:
            result["unit"] = self.unit
        if self.type is not None:
            result["type"] = self.type
        if len(self._threshold_low) > 0:
            result["threshold_low"] = [
                {"name": n, "value": v, "severity": s}
                for (n, (v, s)) in self._threshold_low.iteritems()
            ]
        if len(self._threshold_high) > 0:
            result["threshold_high"] = [
                {"name": n, "value": v, "severity": s}
                for (n, (v, s)) in self._threshold_high.iteritems()
            ]
        return result

    #-----------------------------------------------------------------

    @property
    def name(self):
        '''
        Name of the value (read-only).
        '''
        return self._name

    def _set_name(self, name):
        # private setter
        self._name = name

    #-----------------------------------------------------------------

    @property
    def value(self):
        '''
        Value (read-write).
        '''
        return self._value

    @value.setter
    def value(self, value):
        if value is None:
            self._value = None
        elif isinstance(value, (int, long, float)):
            self._value = value
        else:
            raise ValueError(
                "invalid type of value %s: %s" % (self._name, type(value))
            )

    def __int__(self):
        return int(self._value)

    def __long__(self):
        return long(self._value)

    def __float__(self):
        return float(self._value)

    def __eq__(self, other):
        if other is None:
            return (self._value is None)
        elif isinstance(other, Value):
            return self._value == other._value
        elif isinstance(other, (int, long, float)):
            return self._value == other

    def __gt__(self, other):
        if self._value is None:
            return False
        if isinstance(other, Value):
            other = other._value
        return (other is None or self._value > other)

    def __lt__(self, other):
        if isinstance(other, Value):
            other = other._value
        if other is None:
            return False
        return (self._value is None or self._value < other)

    def __ge__(self, other):
        return (not self < other)

    def __le__(self, other):
        return (not self > other)

    #-----------------------------------------------------------------

    def exceeds(self):
        '''
        :return: name and severity of exceeded threshold or ``None``
        :rtype: tuple (str, str)

        Check which threshold is exceeded (highest from high thresholds or
        lowest from low).
        '''
        name = self.is_above()
        if name is not None:
            return name
        return self.is_below()

    def set_above(self, value, name, severity = 'error'):
        '''
        :param value: value of the threshold
        :param name: name of the threshold
        :param severity: severity of the threshold
        :type severity: ``"warning"`` or ``"error"``
        :return: :obj:`self`

        Add/change high threshold.
        '''
        if not isinstance(value, (int, long, float)):
            raise ValueError(
                "invalid type of threshold %s: %s" % (name, type(value))
            )
        if severity not in ('warning', 'error'): # 'expected' makes no sense
            raise ValueError(
                "invalid severity of threshold %s: %s" % (name, severity)
            )
        self._threshold_high[name] = (value, severity)
        return self

    def set_below(self, value, name, severity = 'error'):
        '''
        :param value: value of the threshold
        :param name: name of the threshold
        :param severity: severity of the threshold
        :type severity: ``"warning"`` or ``"error"``
        :return: :obj:`self`

        Add/change low threshold.
        '''
        if not isinstance(value, (int, long, float)):
            raise ValueError(
                "invalid type of threshold %s: %s" % (name, type(value))
            )
        if severity not in ('warning', 'error'): # 'expected' makes no sense
            raise ValueError(
                "invalid severity of threshold %s: %s" % (name, severity)
            )
        self._threshold_low[name] = (value, severity)
        return self

    def has_thresholds(self):
        '''
        Check if the value has any thresholds.
        '''
        return (len(self._threshold_high) + len(self._threshold_low) > 0)

    def thresholds(self):
        '''
        :return: list of thresholds: ``(name, low, high)``
        :rtype: list of 3-tuples

        Return all defined thresholds: low and high. If only threshold low or
        high for a given name is defined, the other is reported as ``None``.
        '''
        result = []
        for thr in set(self._threshold_high).union(self._threshold_low):
            # just the numbers, not severities
            thr_hi = self._threshold_high.get(thr)
            if thr_hi is not None: thr_hi = thr_hi[0]
            thr_lo = self._threshold_low.get(thr)
            if thr_lo is not None: thr_lo = thr_lo[0]
            result.append((thr, thr_lo, thr_hi))
        return result

    def is_above(self):
        '''
        :return: name and severity of exceeded threshold or ``None``
        :rtype: 2-tuple or ``None``

        Check which high threshold is exceded (value > threshold).
        '''
        if self._value is None:
            return None

        above_name = None
        above_value = None
        above_severity = None
        for (name, (value, severity)) in self._threshold_high.iteritems():
            # 1. exceeds threshold
            # 2. old threshold is worse (or not set at all)
            if self._value > value and \
               (above_value is None or above_value < value):
                above_name = name
                above_value = value
                above_severity = severity
        if above_name is None:
            return None
        else:
            return (above_name, above_severity)

    def is_below(self):
        '''
        :return: name and severity of exceeded threshold or ``None``
        :rtype: 2-tuple or ``None``

        Check which low threshold is exceded (value < threshold).
        '''
        if self._value is None:
            return None

        below_name = None
        below_value = None
        below_severity = None
        for (name, (value, severity)) in self._threshold_low.iteritems():
            # 1. value exceeds threshold
            # 2. old threshold is worse (or not set at all)
            if self._value < value and \
               (below_value is None or below_value > value):
                below_name = name
                below_value = value
                below_severity = severity
        if below_name is None:
            return None
        else:
            return (below_name, below_severity)

    def remove_threshold(self, name, which = 'both'):
        '''
        :param name: name of threshold to remove
        :param which: which
        :type which: ``"above"`` (``"high"``), ``"below"`` (``"low"``) or
            ``"both"``

        Remove threshold (high, low or both).
        '''
        if which in ('both', 'above', 'high') and name in self._threshold_high:
            del self._threshold_high[name]
        if which in ('both', 'below', 'low') and name in self._threshold_low:
            del self._threshold_low[name]

    #-----------------------------------------------------------------

    @property
    def unit(self):
        '''
        Unit of measurement (read-write-delete).
        '''
        return self._unit

    @unit.setter
    def unit(self, unit):
        self._unit = unit

    @unit.deleter
    def unit(self):
        self._unit = None

    #-----------------------------------------------------------------

    @property
    def type(self):
        '''
        Type of change: direct, accumulative (integral of actual value) or
        differential (read-wite-delete).
        '''
        return self._type

    @type.setter
    def type(self, type):
        if type not in ("direct", "accumulative", "differential", None):
            raise ValueError(
                "invalid change type for value %s: %s" % (self._name, type)
            )
        self._type = type

    @type.deleter
    def type(self):
        self._type = None

    #-----------------------------------------------------------------

#-----------------------------------------------------------------------------

class Location(object):
    '''
    Dictionary-like object that checks if elements have valid names/types for
    location.
    '''
    def __init__(self, location):
        self._location = {}
        if location is not None:
            # shallow copy that triggers all the checks
            for l in location:
                self[l] = location[l]

    def get(self, name, default = None):
        '''
        Return location field without raising an exception on undefined key.
        '''
        if name not in self._location:
            return default
        return self._location[name]

    def __getitem__(self, name):
        if name not in self._location:
            raise KeyError('no such location: %s' % (name,))
        return self._location[name]

    def __setitem__(self, name, value):
        # TODO: check value_name against regexp
        if not isinstance(value, (str, unicode)):
            raise ValueError("location must be a string")
        self._location[name] = value

    def __delitem__(self, name):
        if name in self._location:
            del self._location[name]

    def __contains__(self, name):
        return (name in self._location)

    def __len__(self):
        return len(self._location)

    def __iter__(self):
        return self._location.__iter__()

    def keys(self):
        '''
        Retrieve location keys.
        '''
        return self._location.keys()

    def values(self):
        '''
        Retrieve location values.
        '''
        return self._location.values()

    def items(self):
        '''
        Retrieve location (key,value) pairs.
        '''
        return self._location.items()

    def iteritems(self):
        '''
        Retrieve location (key,value) pairs as an iterator.
        '''
        return self._location.iteritems()

    def copy(self):
        '''
        Duplicate the instance as a dict.
        '''
        return self._location.copy()

    def to_dict(self):
        '''
        Convert the instance to dict.
        '''
        return self._location.copy()

    def __repr__(self):
        if len(self._location) == 0:
            return "<Location {}>"
        s = ["%s=%s" % (k,v) for (k,v) in self._location.iteritems()]
        s.sort()
        return "<Location {%s}>" % (" ".join(s))

#-----------------------------------------------------------------------------

class Message(object):
    '''
    Class representing single message suitable for Seismometer.

    An instance supports dict-like interface to access values
    (``event.vset.*``). ``len(instance)`` returns a number of values in value
    set. Each value is an instance of :class:`Value` class. Setting a value to
    integer, float or ``None`` results in creating new :class:`Value`. Setting
    it to :class:`Value` *does not copy* the original value.

    If a message does not conform to schema, :exc:`ValueError` is thrown.
    '''

    # TODO: remember other data carried by the message

    def __init__(self, message = None,
                 time = None, interval = None, aspect = None, location = None,
                 state = None, severity = None, comment = None,
                 value = _NOTHING):
        '''
        :param message: message to create representation for
        :param time: unix timestamp of event; defaults to ``time.time()``
        :type time: integer
        :param interval: interval at which event is generated
        :type interval: number of seconds
        :param aspect: monitored aspect's name
        :type aspect: string
        :param location: where the monitored aspect is located
        :type location: dictionary(str => str)
        :param state: state of the monitored aspect
        :type state: string
        :param severity: what type is the aspect's state
        :type severity: ``expected``, ``warning`` or ``error``
        :param comment: comment on monitored aspect's state
        :type comment: string
        :param value: set value named ``"value"`` to this value
        :type value: float, integer or ``None``

        Either :obj:`message` or rest of the parameters should be set.
        '''

        # create representation of an existing message
        # XXX: don't bother with the case when user provided message and
        # anything except it -- make it GIGO
        if message is not None:
            try:
                self._fill_message(message)
            except KeyError:
                # TODO: pass some more details
                raise ValueError("message doesn't conform to schema")
            return

        # fill the properties
        self._v = SCHEMA_VERSION
        self.time = time
        self.interval = interval
        self.aspect = aspect
        self._location = Location(location) # no setter here
        self.state = state
        self._severity = None
        if severity is not None:
            self.severity = severity
        self.comment = comment
        self._vset = {} # no setter here
        self._threshold_kept = None

        if not isinstance(aspect, (str, unicode)):
            raise ValueError("aspect name must be string")

        # create fresh message, filling what was provided to constructor
        # actually, finish the message

        # set value if provided
        if value is not _NOTHING:
            self["value"] = value

    #-----------------------------------------------------------------
    # constructor helper for existing message

    def _fill_message(self, message):
        '''
        Initialize the instance with values read from an incoming message.
        '''
        if "v" not in message or "event" not in message:
            raise ValueError("not a seismometer.message")
        if message["v"] != 3:
            raise ValueError("wrong schema version: %s" % (message["v"],))

        event = message["event"] # convenience variable

        self._v = SCHEMA_VERSION
        self.time = message["time"]
        self.interval = event.get("interval")
        self.aspect = event["name"]
        self._location = Location(message["location"]) # no setter here
        self._state = None    # initial value
        self._severity = None # initial value
        self._comment = None  # initial value
        self._threshold_kept = None # initial value
        self._vset = {} # no setter here
        if "state" in event:
            self.state = event["state"]["value"]
            if "severity" in event["state"]:
                self.severity = event["state"]["severity"]
        if "comment" in event:
            self.comment = event["comment"]
        if "threshold_kept" in event:
            self.threshold_kept = event["threshold_kept"]
        if "vset" in event:
            for (name,value) in event["vset"].iteritems():
                self[name] = Value(
                    name = name,
                    value = value["value"],
                    unit = value.get("unit"),
                    type = value.get("type"),
                )
                for thr in value.get("threshold_high", ()):
                    self[name].set_above(
                        thr["value"], thr["name"], thr["severity"]
                    )
                for thr in value.get("threshold_low", ()):
                    self[name].set_below(
                        thr["value"], thr["name"], thr["severity"]
                    )

    #-----------------------------------------------------------------
    # property accessors

    @property
    def v(self):
        '''
        Base schema version this message conforms to. (read-only)

        Equals to :const:`SCHEMA_VERSION`.
        '''
        return self._v

    #-----------------------------------------------------------------

    @property
    def time(self):
        '''
        Unix timestamp at which the event occurred. (read-write-delete)
        '''
        return self._time

    @time.setter
    def time(self, time):
        if time is None:
            time = now()
        self._time = int(time)

    @time.deleter
    def time(self):
        self._time = int(now())

    #-----------------------------------------------------------------

    @property
    def interval(self):
        '''
        Interval at which the event is generated. ``None`` means the event is
        not generated on a regular basis. (read-write-delete)
        '''
        return self._interval

    @interval.setter
    def interval(self, interval):
        self._interval = interval

    @interval.deleter
    def interval(self):
        self._interval = None

    #-----------------------------------------------------------------

    @property
    def aspect(self):
        '''
        Name of the monitored aspect this message refers to. (read-write)
        '''
        return self._aspect

    @aspect.setter
    def aspect(self, aspect):
        self._aspect = aspect

    # XXX: no deleter

    #-----------------------------------------------------------------

    @property
    def location(self):
        '''
        Location dictionary(-like). Keys and values are both strings.
        (read-write)

        Individual keys can be added/deleted as with typical dictionary.
        To reset location wholly a dictionary can be assigned to this
        attribute.
        '''
        return self._location

    @location.setter
    def location(self, location):
        self._location = Location(location)

    #-----------------------------------------------------------------

    @property
    def state(self):
        '''
        State carried by the event. (read-write-delete)

        Deleting the state deletes also :attr:`severity`.
        '''
        return self._state

    @state.setter
    def state(self, state):
        # TODO: check state against regexp
        self._state = state

    @state.deleter
    def state(self):
        self._state = None
        self._severity = None # unset also the severity

    #-----------------------------------------------------------------

    @property
    def severity(self):
        '''
        Severity of the :attr:`state`. (read-write-delete)

        Either ``"expected"``, ``"warning"`` or ``"error"``.
        '''
        return self._severity

    @severity.setter
    def severity(self, severity):
        if severity not in ('expected', 'warning', 'error'):
            raise ValueError("invalid severity: %s" % (severity,))
        self._severity = severity

    @severity.deleter
    def severity(self):
        self._severity = None

    #-----------------------------------------------------------------

    @property
    def comment(self):
        '''
        Description of the :attr:`state` readable by user. (read-write-delete)
        '''
        return self._comment

    @comment.setter
    def comment(self, comment):
        self._comment = comment

    @comment.deleter
    def comment(self):
        self._comment = None

    #-----------------------------------------------------------------

    @property
    def threshold_kept(self):
        '''
        What :attr:`state` to assume when all thresholds for values are kept.

        Note that setting this attribute doesn't make :attr:`state` magically
        appear. It's informative only.
        '''
        return self._threshold_kept

    @threshold_kept.setter
    def threshold_kept(self, value):
        self._threshold_kept = value

    @threshold_kept.deleter
    def threshold_kept(self):
        self._threshold_kept = None

    #-----------------------------------------------------------------
    # value set

    def __getitem__(self, value_name):
        if value_name not in self._vset:
            raise KeyError('no such value: %s' % (value_name,))
        return self._vset[value_name]

    def __setitem__(self, value_name, value):
        # TODO: check value_name against regexp
        if isinstance(value, Value):
            # instance of Value is expected to be a temporary variable
            # we'll can claim ownership of the variable
            self._vset[value_name] = value
            self._vset[value_name]._set_name(value_name)
        else:
            self._vset[value_name] = Value(value, value_name)

    def __delitem__(self, value_name):
        if value_name in self._vset:
            del self._vset[value_name]

    def __contains__(self, value_name):
        return (value_name in self._vset)

    def __len__(self):
        return len(self._vset)

    def __iter__(self):
        return self._vset.__iter__()

    def keys(self):
        '''
        Retrieve names of the values this message carries.
        '''
        return self._vset.keys()

    def values(self):
        '''
        Retrieve value instances (:class:`Value`) this message carries.
        '''
        return self._vset.values()

    def items(self):
        '''
        Retrieve values as (name,instance) pairs.
        '''
        return [i for i in self.iteritems()]

    def iteritems(self):
        '''
        Retrieve values as (name,instance) pairs (iterator).
        '''
        for v in self:
            yield (v, self[v])

    def exceeds(self):
        '''
        :return: tuple (threshold,severity) or ``None``

        Check if any of the values carried exceed its threshold. If more than
        one value exceeds a threshold, an arbitrary one is returned.
        '''
        for value in self:
            result = self[value].exceeds()
            if result is not None:
                return result
        return None

    #-----------------------------------------------------------------

    def copy(self):
        '''
        Return a deep copy of the message instance.
        '''
        result = Message(
            time = self.time, interval = self.interval,
            aspect = self.aspect, location = self._location._location,
            state = self.state, severity = self.severity,
            comment = self.comment
        )
        for val in self:
            result[val] = self[val].copy()
        return result

    def to_dict(self):
        '''
        Create a dictionary representing the message.

        The result shares nothing with the original message, so can be safely
        modified after creation.
        '''
        event = { "name": self.aspect }

        # fill in value set
        if len(self) > 0:
            event["vset"] = {}
            for name in self:
                event["vset"][name] = self[name].to_dict()

        # fill in state
        if self.state is not None:
            event["state"] = { "value": self.state }
            if self.severity is not None:
                event["state"]["severity"] = self.severity

        if self.comment is not None:
            event["comment"] = self.comment
        if self.interval is not None:
            event["interval"] = self.interval
        if self.threshold_kept is not None:
            event["threshold_kept"] = self.threshold_kept

        message = {
            "v": self.v,
            "time": self.time,
            # this must be present even if empty
            "location": self.location.to_dict(),
            "event": event
        }

        return message

    #-----------------------------------------------------------------

#-----------------------------------------------------------------------------

def is_valid(message):
    '''
    :param message: object to check
    :return: ``True`` if :obj:`message` is a dictionary with Seismometer
         structure, ``False`` otherwise

    Function to tell dictionary with a Seismometer message from other
    dictionaries and objects.
    '''
    # XXX: this is a simple check, but it will weed out pretty much everything
    # that is intended to be a metric or state message
    return isinstance(message, dict) and \
           message.get("v") == SCHEMA_VERSION and \
           "event" in message and \
           isinstance(message["event"].get("name"), (str, unicode)) and \
           isinstance(message.get("time"), (int, long, float)) and \
           isinstance(message.get("location", {}), dict)

#-----------------------------------------------------------------------------
# vim:ft=python
