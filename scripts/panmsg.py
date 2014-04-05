#!/usr/bin/python
#
# Class set for handling panopticon messages
#
#-----------------------------------------------------------------------------

class Threshold(object):
    def __init__(self, threshold):
        self.threshold = threshold

    def get_name(self):
        return self.threshold["name"]

    def get_value(self):
        return self.threshold["value"]

#-----------------------------------------------------------------------------

class VSetProperty(object):
    def __init__(self, property):
        self.property = property

    def get_value(self):
        return self.property["value"]

    def get_unit(self):
        if "unit" in property.keys():
            return self.property["unit"]
        else:
            return None

    def get_type(self):
        if "type" in self.property.keys():
            return self.property["type"]
        else:
            return None

    def get_thresholds_low(self):
        if "threshold_low" in self.property.keys():
            thresholds = []
            for threshold in self.property["threshold_low"]:
                thresholds.append(Threshold(threshold))
            return thresholds
        else:
            return None

    def get_thresholds_high(self):
        if "threshold_high" in self.property.keys():
            thresholds = []
            for threshold in self.property["threshold_high"]:
                thresholds.append(Threshold(threshold))
            return thresholds
        else:
            return None

    def get_threshold_kept(self):
        if "threshold_kept" in self.property.keys():
            return self.property["threshold_kept"]
        else:
            return "ok"
#-----------------------------------------------------------------------------

class State(object):
    def __init__(self, state):
        self.state = state

    def get_value(self):
        return self.state["value"]

    def get_expected(self):
        if "expected" in self.state.keys():
            return self.state["expected"]
        else:
            return None

    def get_attention(self):
        if "attention" in self.state.keys():
            return self.state["attention"]
        else:
            return None

    def set_value(self, value):
        self.state["value"] = value

    def set_expected(self, expected):
        self.state["expected"] = expected

    def set_attention(self, attention):
        self.state["attention"] = attention

#-----------------------------------------------------------------------------

class Event(object):
    def __init__(self, event):
        self.event = event

    def get_name(self):
        return self.event["name"]

    def get_state(self):
        if "state" in self.event.keys():
            return State(self.event["state"])
        else:
            return None

    def get_comment(self):
        if "comment" in self.event.keys():
            return self.event["comment"]
        else:
            return None

    def get_vset_keys(self):
        if "vset" in self.event.keys():
            return self.event["vset"].keys()
        else:
            return None

    def get_vset(self, key):
        if "vset" in self.event.keys() and key in self.event["vset"].keys():
            return VSetProperty(self.event["vset"][key])
        else:
            return None

    def set_state(self, state, expected, attention):
        if "state" not in self.event.keys():
            self.event["state"] = {}
        self.get_state().set_value(state)
        self.get_state().set_expected(expected)
        self.get_state().set_attention(attention)

#-----------------------------------------------------------------------------

class Message(object):
    """description of class"""

    def __init__(self, message):
        self.message = message

    def get_version(self):
        return self.message["v"]

    def get_time(self):
        return self.message["time"]

    def get_location_keys():
        return self.message["location"].keys()

    def get_location(self, key):
        if key in self.message["location"].keys():
            return self.message["location"][key]
        else:
            return None

    def get_event(self):
        return Event(self.message["event"])
