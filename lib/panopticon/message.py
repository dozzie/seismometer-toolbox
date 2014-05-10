#!/usr/bin/python
#
# Class set for handling panopticon messages
#
#-----------------------------------------------------------------------------

import time

class Threshold(object):
    def __init__(self, *args):
        if args[0] is not None:
            if isinstance(args[0], Threshold):
                self.name = threshold.name
                self.value = threshold.value
                self.severity = threshold.severity
            else: #isinstance(threshold, dict):
                self.name = args[0]["name"]
                self.value = args[0]["value"]
                self.severity = args[0]["severity"]
        else: #name is not None:
            self.name = args[0]
            self.value = args[1]
            self.severity = args[2]

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    @property
    def severity(self):
        return self.__severity

    @severity.setter
    def severity(self, severity):
        self.__severity = severity

    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value,
            "severity": self.severity
        }

#-----------------------------------------------------------------------------

class VSetProperty(object):
    def __init__(self, property):
        if isinstance(property, VSetProperty):
            self.value = property.value
            self.unit = property.unit
            self.type = property.type
            self.threshold_low = property.threshold_low
            self.threshold_high = property.threshold_high
        elif isinstance(property, dict):
            self.value = property["value"]
            if property.has_key("unit"):
                self.unit = property["unit"]
            if property.has_key("type"):
                self.type = property["type"]
            if property.has_key("threshold_low"):
                self.threshold_low = []
                for threshold in property["threshold_low"]:
                    self.threshold_low.append(Threshold(threshold))
            if property.has_key("threshold_high"):
                self.threshold_high = []
                for threshold in property["threshold_high"]:
                    self.threshold_high.append(Threshold(threshold))
        else:
            self.__value = property

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    @property
    def unit(self):
        if hasattr(self, "_VSetProperty__unit"):
            return self.__unit
        else:
            return None

    @unit.setter
    def unit(self, unit):
        if unit is not None:
            self.__unit = unit

    @unit.deleter
    def unit(self):
        del self.__unit

    @property
    def type(self):
        if hasattr(self, "_VSetProperty__type"):
            return self.__type
        else:
            return None

    @type.setter
    def type(self, type):
        if type is not None:
            if type not in ["direct", "accumulative", "differential"]:
                raise ValueError("Not allowed value for type.")
            self.__type = type

    @type.deleter
    def type(self):
        del self.__type

    @property
    def threshold_low(self):
        if hasattr(self, "_VSetProperty__threshold_low"):
            return self.__threshold_low
        else:
            return None

    @threshold_low.setter
    def threshold_low(self, threshold):
        if threshold is not None:
            self.__threshold_low = threshold

    @threshold_low.deleter
    def threshold_low(self):
        del self.__threshold_low

    @property
    def threshold_low_dict(self):
        if self.threshold_low is not None:
            t = []
            for threshold in self.threshold_low:
                t.append(threshold.to_dict())
            return t
        else:
            return None

    @property
    def threshold_high(self):
        if hasattr(self, "_VSetProperty__threshold_high"):
            return self.__threshold_high
        else:
            return None

    @threshold_high.setter
    def threshold_high(self, threshold):
        if threshold is not None:
            self.__threshold_high = threshold

    @threshold_high.deleter
    def threshold_high(self):
        del self.__threshold_high

    @property
    def threshold_high_dict(self):
        if self.threshold_high is not None:
            t = []
            for threshold in self.threshold_high:
                t.append(threshold.to_dict())
            return t
        else:
            return None

    def to_dict(self):
        vset = {
             "value": self.value
        }
        if self.unit is not None:
            vset["unit"] = self.unit
        if self.type is not None:
            vset["type"] = self.type
        if self.threshold_low is not None:
            vset["threshold_low"] = self.threshold_low_dict
        if self.threshold_high is not None:
            vset["threshold_high"] = self.threshold_high_dict
        return vset

#-----------------------------------------------------------------------------

class State(object):
    def __init__(self, state):
        if isinstance(state, State):
            self.value = state.value
            if state.severity is not None:
                self.severity = state.severity
        elif isinstance(state, dict):
            self.value = state["value"]
            if state.has_key("severity"):
                self.severity = state["severity"]
        else:
            self.__value = state

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    @property
    def severity(self):
        if hasattr(self, "_State__severity"):
            return self.__severity
        else:
            return None

    @severity.setter
    def severity(self, severity):
        self.__severity = severity

    @severity.deleter
    def severity(self):
        del self.__severity

    def to_dict(self):
        state = {
            "value": self.value
        }
        if self.severity is not None:
            state["severity"] = self.severity

        return state

#-----------------------------------------------------------------------------

class Event(object):
    def __init__(self, event):
        if isinstance(event, Event):
            self.name = event.name
            if event.state is not None:
                self.state = event.state
            if event.comment is not None:
                self.comment = event.comment
            if event.interval is not None:
                self.interval = event.interval
            if event.vset is not None:
                self.vset = event.vset
            if event.threshold_kept is not None:
                self.threshold_kept = event.threshold_kept
        elif isinstance(event, dict):
            self.name = event["name"]
            if event.has_key("state"):
                self.state = State(event["state"])
            if event.has_key("comment"):
                self.state = event["comment"]
            if event.has_key("interval"):
                self.interval = event["interval"]
            if event.has_key("vset"):
                self.vset = {}
                for key in event["vset"]:
                    self.vset[key] = VSetProperty(event["vset"][key])
            if event.has_key("threshold_kept"):
                self.threshold_kept = event["threshold_kept"]
        else:
            self.__name = event

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def state(self):
        if hasattr(self, "_Event__state"):
            return self.__state
        else:
            return None

    @state.setter
    def state(self, state):
        if state is not None:
            self.__state = state

    @state.deleter
    def state(self):
        del self.__state

    @property
    def comment(self):
        if hasattr(self, "_Event__comment"):
            return self.__comment
        else:
            return None
    
    @comment.setter
    def comment(self, comment):
        if comment is not None:
            self.__comment = comment

    @comment.deleter
    def comment(self):
        del self.__comment

    @property
    def interval(self):
        if hasattr(self, "_Event__interval"):
            return self.__interval
        else:
            return None

    @interval.setter
    def interval(self, interval):
        self.__interval = interval

    @interval.deleter
    def interval(self):
        del self.__interval

    @property
    def vset(self):
        if hasattr(self, "_Event__vset"):
            return self.__vset
        else:
            return None

    @vset.setter
    def vset(self, vset):
        if vset is not None:
            self.__vset = vset
    
    @vset.deleter
    def vset(self):
        del self.__vset

    @property
    def vset_dict(self):
        if self.vset is not None:
            v = {}
            for key in self.vset:
                v[key] = self.vset[key].to_dict()
            return v
        else:
            return None

    @property
    def threshold_kept(self):
        if hasattr(self, "_Event__threshold_kept"):
            return self.__threshold_kept
        else:
            return None

    @threshold_kept.setter
    def threshold_kept(self, threshold_kept):
        self.__threshold_kept = threshold_kept

    @threshold_kept.deleter
    def threshold_kept(self):
        del self.__threshold_kept

    def to_dict(self):
        event = {
            "name": self.name
        }
        if self.state is not None:
            event["state"] = self.state.to_dict()
        if self.comment is not None:
            event["comment"] = self.comment
        if self.interval is not None:
            event["interval"] = self.interval
        if self.vset is not None:
            event["vset"] = self.vset_dict
        if self.threshold_kept is not None:
            event["threshold_kept"] = self.threshold_kept
        return event

#-----------------------------------------------------------------------------
        
class Message(object):
    def __init__(self, *args):
        if isinstance(args[0], Message):
            self.time = args[0].time
            self.location = args[0].location
            self.event = args[0].location
        elif isinstance(args[0], dict):
            self.time = args[0]["time"]
            self.location = args[0]["location"]
            self.event = Event(args[0]["event"])
        else:
            self.time = args[0]
            self.location = args[1]
            self.event = args[2]

    @property
    def v(self):
        return 3

    @property
    def time(self):
        return self.__time

    @time.setter
    def time(self, time):
        self.__time = time

    @property
    def location(self):
        return self.__location

    @location.setter
    def location(self, location):
        if not isinstance(location, dict):
            raise TypeError("location must be a dict.")
        self.__location = location

    @property
    def event(self):
        return self.__event

    @event.setter
    def event(self, event):
        self.__event = event

    def to_dict(self):
        message = {
            "v": self.v,
            "time": self.time,
            "location": self.location,
            "event": self.event.to_dict()
        }
        return message
