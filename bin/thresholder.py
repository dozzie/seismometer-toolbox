#!/usr/bin/python
#
# Thresholder for Panopticon streem
#
# Verifies trhesholds given in messages and adds measured aspect state,
# then sends message to another streem

import sys
import socket
import json
import argparse
import panopticon.message
import streem

#-----------------------------------------------------------------------------
# Creates commandline argument parser
def create_parser():
    parser = argparse.ArgumentParser(
        description="Monitors Panopticons probe messages"
    )
    parser.add_argument('--host', '-a', dest='host', type=str,
        required=True, help='Destination streem host')
    parser.add_argument('--port', '-p', dest='port', type=int,
        required=True, help='Destination streem port')
    parser.add_argument('--src-channel', '-s', dest='srcchannel', type=str,
        default='probes', help='Source streem channel')
    parser.add_argument('--dst-channel', '-d', dest='dstchannel', type=str,
        default='states', help='Destination streem channel')
    return parser

#-----------------------------------------------------------------------------
# Get state names from given threshold array
#def get_threshold_states(thresholds):
#    states = []
#    if thresholds is not None:
#        for threshold in thresholds:
#            states.append({"name": threshold.name, "severity": threshold.severity})
#    return states

#-----------------------------------------------------------------------------
# Gets state names based on vset properties
#def get_states(message):
#    attention_states = []
#    expected_state = message.event.threshold_kept
#    if message.event.vset is not None:
#        for key, vset in message.event.vset.iteritems():
#            attention_states.extend(
#                get_threshold_states(vset.threshold_low))
#            attention_states.extend(
#                get_threshold_states(vset.threshold_high))

#    return [expected_state, sorted(set(attention_states))]

def has_thresholds(message):
    if message.event.vset is not None:
        for key, vset in message.event.vset.iteritems():
            if vset.threshold_low is not None \
                and vset.threshold_low != []:
                return True
            elif vset.threshold_high is not None \
                and vset.threshold_high != []:
                return True
    return False

#-----------------------------------------------------------------------------
# Gets most exceeded threshold for given vset (based on severity and value)
def get_exceeded_threshold(vset):
    threshold_low = None
    threshold_high = None
    if vset.value is not None:
        if vset.threshold_low is not None:
            for threshold in vset.threshold_low:
                if (threshold_low is None \
                    or threshold.value < threshold_low.value) \
                    and vset.value < threshold.value:
                    threshold_low = threshold
        if vset.threshold_high is not None:
            for threshold in vset.threshold_high:
                if (threshold_high is None \
                    or threshold.value > threshold_high.value) \
                    and vset.value > threshold.value:
                    threshold_high = threshold
    if threshold_high is not None and threshold_high.severity == "error":
        return threshold_high
    elif threshold_low is not None and threshold_low.severity == "error":
        return threshold_low
    elif threshold_high is not None:
        return threshold_high
    elif threshold_low is not None:
        return threshold_low
    else:
        return None

#-----------------------------------------------------------------------------
# Gets overall most exceeded threshold (based on severity)
def get_threshold(message):
    warning = None
    threshold = None
    if message.event.vset is not None:
        for key, vset in message.event.vset.iteritems():
            threshold = get_exceeded_threshold(vset)
            if threshold is not None:
                if threshold.severity == "error":
                    return threshold
                elif warning is None:
                    warning = threshold
    return warning

#-----------------------------------------------------------------------------
# Gets aspects state based on all vset data
def get_state(message):
    state = None
    if message.event.vset is not None:
        for key, vset in message.event.vset.iteritems():
            state = get_threshold_state(vset)
            if state is not None:
                break
    if state is None:
        state = "ok"
    return state 

#-----------------------------------------------------------------------------

# Parse arguments
parser = create_parser()
args = parser.parse_args()

try:
    # Streem initialization
    conn = streem.Streem(args.host, args.port)
    conn.register(args.dstchannel)
    conn.subscribe(args.srcchannel)

    # Main loop
    while True:
        reply = conn.receive()
        # TODO: Add schema validation
        message = panopticon.message.Message(reply)
        if message.v != 3:
            continue

        if not has_thresholds(message):
            continue

        # TODO: Get exceeeded threshold
        threshold = get_threshold(message)

        state = None
        if threshold is not None:
            state = panopticon.message.State(threshold.name)
            state.severity = threshold.severity
        else:
            if message.event.threshold_kept is not None:
                state = panopticon.message.State(message.event.threshold_kept)
                state.severity = "expected"
            else:
                state = panopticon.message.State("ok")
                state.severity = "expected"

        message.event.state = state

        msg = message.to_dict()
        print json.dumps(message.to_dict())

        conn.submit(message.to_dict())

except streem.ProtocolError as e:
    print "Streem returned status %s." % e.args
except KeyboardInterrupt:
    pass
