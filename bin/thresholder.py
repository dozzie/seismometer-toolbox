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

def has_thresholds(message):
    for v in message:
        if message[v].has_thresholds():
            return True
    return False

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
        try:
            message = panopticon.message.Message(message = reply)
        except ValueError:
            continue

        if message.v != 3:
            continue

        if not has_thresholds(message):
            continue

        # TODO: Get exceeeded threshold
        exceeded = message.exceeds()
        if exceeded is None:
            if message.threshold_kept is None:
                message.state = "ok"
            else:
                message.state = message.threshold_kept
            message.severity = "expected"
        else:
            message.state = exceeded[0]
            message.severity = exceeded[1]

        msg = message.to_dict()
        print json.dumps(message.to_dict())

        conn.submit(message.to_dict())

except streem.ProtocolError as e:
    print "Streem returned status %s." % e.args
except KeyboardInterrupt:
    pass
