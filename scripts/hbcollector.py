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
import panmsg
import streem

#-----------------------------------------------------------------------------
# Creates commandline parser
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
    parser.add_argument('--db-name', '-db', dest='dbname', type=str,
        default='hbdb.db', help='Heartbeat database name')
    return parser

#-----------------------------------------------------------------------------
# Gets data identyfying message
def get_message_key(message):
    key = {
        "location": message["location"],
        "event": {
            "name": message["event"]["name"]
        }
    }
    return json.dumps(key)

#-----------------------------------------------------------------------------
# Creates state message
def create_state_message(message, state):
    state_message = {
        "v": 2,
        "time": round(time.time()),
        "location": message["location"],
        "event": {
            "name": message["event"]["name"],
            "state": state,
            "expected": ["up"],
            "attention": ["down"]
        }
    }
    return state_message

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
        message = conn.receive()
        # TODO: Add schema validation
        if message["v"] != 2:
            continue

        key = get_message_key(message)
        if not db.has_key(key):
            state_message = create_state_message(message, "up")
            conn.submit(state_message)

        db[key] = str(message["time"])
        db.sync()

except streem.ProtocolError as e:
    print "Streem returned status %s." % e.args
except KeyboardInterrupt:
    pass
finally:
    db.close()
