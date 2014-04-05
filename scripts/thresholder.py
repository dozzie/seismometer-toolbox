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
import panmsg
import streem

#-----------------------------------------------------------------------------
# Creates commandline argument parser
def create_parser():
    parser = argparse.ArgumentParser(
        description="Monitors Panopticons probe messages"
    )
    parser.add_argument('--host', dest='host', type=str,
        required=True, help='Destination streem host')
    parser.add_argument('--port', dest='port', type=int,
        required=True, help='Destination streem port')
    parser.add_argument('--src-channel', dest='srcchannel', type=str,
        default='probes', help='Source streem channel')
    parser.add_argument('--dst-channel', dest='dstchannel', type=str,
        default='states', help='Destination streem channel')
    return parser

#-----------------------------------------------------------------------------
# Gets state names based on vset properties
def get_states(message):
    attention_states = []
    expected_states = []
    vset_keys = message.get_event().get_vset_keys()
    if vset_keys is not None and vset_keys:
        for key in vset_keys:
            vset = message.get_event().get_vset(key)
            thresholds_low = vset.get_thresholds_low()
            if thresholds_low is not None:
                for threshold in thresholds_low:
                    attention_states.append(threshold.get_name())
            thresholds_high = vset.get_thresholds_high()
            if thresholds_high is not None:
                for threshold in thresholds_high:
                    attention_states.append(threshold.get_name())
            threshold_kept = vset.get_threshold_kept()
            if threshold_kept not in expected_states:
                expected_states.append(threshold_kept)
    return [expected_states, attention_states]

#-----------------------------------------------------------------------------
# Gets aspect state based on thresholds
def get_threshold_state(vset):
    threshold_low = None
    threshold_high = None
    value = vset.get_value();
    if value is not None:
        thresholds_low = vset.get_thresholds_low()
        if thresholds_low is not None:
            for threshold in thresholds_low:
                if (threshold_low is None \
                    or threshold.get_value() < threshold_low.get_value()) \
                    and value > threshold.get_value():
                    threshold_low = threshold
        thresholds_high = vset.get_thresholds_high()
        if thresholds_high is not None:
            for threshold in thresholds_high:
                if (threshold_high is none \
                    or threshold.get_value() > threshold_high.get_value()) \
                    and value < threshold.get_value():
                    threshold_high = threshold
    if threshold_high is not None:
        return threshold_high.get_name()
    else:
        if threshold_low is not None:
            return threshold_low.get_name()
        else:
            return None
                    
#-----------------------------------------------------------------------------
# Gets aspects state based on all vset data
def get_state(message):
    states = []
    vset_keys = message.get_event().get_vset_keys()
    if vset_keys is not None and vset_keys:
        for key in vset_keys:
            vset = message.get_event().get_vset(key)
            state = get_threshold_state(vset)
            if state is not None:
                states.append(state)
    if states:
        return states[0]
    else:
        return "ok"

#-----------------------------------------------------------------------------

parser = create_parser()
args = parser.parse_args()

#-----------------------------------------------------------------------------

host = args.host
port = args.port
srcchannel = args.srcchannel
dstchannel = args.dstchannel

#-----------------------------------------------------------------------------

try:
    # Streem initialization
    streem = streem.Streem(host, port)
    streem.register(dstchannel)
    streem.subscribe(srcchannel)

    # Main loop
    while True:
        reply = streem.receive()
        if 'message' in reply:
            # TODO: Add schema validation
            message = panmsg.Message(reply["message"])
            if message.get_version() != 2:
                continue

            states = get_states(message)
            state = get_state(message)
            message.get_event().set_state(state, states[0], states[1])
            streem.submit(message.message)

except sjcp.ProtocolError as e:
    print "Streem returned status %s." % e.args
except KeyboardInterrupt:
    pass
