#!/usr/bin/python
#
# Data collector for heartbeat monitor
#
# Stores last timestamp of message identified by location and event name

import sys
import socket
import argparse
import time
import json
import bsddb
import seismometer.message
import streem

#-----------------------------------------------------------------------------
# Creates commandline parser
def create_parser():
    parser = argparse.ArgumentParser(
        description="Monitors Seismometer's probe messages"
    )
    parser.add_argument('--host', '-a', dest='host', type=str,
        required=True, help='Destination streem host')
    parser.add_argument('--port', '-p', dest='port', type=int,
        required=True, help='Destination streem port')
    parser.add_argument('--src-channel', '-s', dest='srcchannel', type=str,
        default='probes', help='Source streem channel')
    parser.add_argument('--dst-channel', '-d', dest='dstchannel', type=str,
        default='states', help='Destination streem channel')
    parser.add_argument('--db-name', '-db', dest='dbname', type=str,
        default='hbdb.db', help='Heartbeat database name')
    return parser

#-----------------------------------------------------------------------------
# Gets data identyfying message
def get_message_key(message):
    key = {
        "location": message.location.to_dict(),
        "event": { "name": message.aspect }
    }
    return json.dumps(key, sort_keys = True)

#-----------------------------------------------------------------------------
# Parse commandline arguments
parser = create_parser()
args = parser.parse_args()

try:
    # Open/create database
    db = bsddb.hashopen(args.dbname, "c")

    # Streem initialization
    conn = streem.Streem(args.host, args.port)
    conn.register(args.dstchannel)
    conn.subscribe(args.srcchannel)

    # Main loop
    while True:
        json_message = conn.receive()
        try:
            message = seismometer.message.Message(message = json_message)
        except ValueError:
            continue

        key = get_message_key(message)
        if not db.has_key(key):
            state_message = seismometer.message.Message(
                aspect = message.aspect,
                location = message.location,
                state = "up",
                severity = "expected",
            )
            conn.submit(state_message.to_dict())

        db[key] = str(message.time)
        db.sync()

except streem.ProtocolError as e:
    print "Streem returned status %s." % e.args
except KeyboardInterrupt:
    pass
finally:
    db.close()
