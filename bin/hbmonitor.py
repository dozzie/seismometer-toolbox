#!/usr/bin/python
#
# Heartbeat monitor
#
# Verifies timestamps of messages and notifies, if timestamp of given message
# was not refreshed for too long time

import sys
import socket
import time
import argparse
import json
import bsddb
import panopticon.message
import streem

#-----------------------------------------------------------------------------
# Creates commandline parser
def create_parser():
    parser = argparse.ArgumentParser(description="Monitors Panopticons probe messages")
    parser.add_argument('--host', '-a', dest='host', type=str,
        required=True, help='Destination streem host')
    parser.add_argument('--port', '-p', dest='port', type=int,
        required=True, help='Destination streem port')
    parser.add_argument('--channel', '-c', dest='channel', type=str, 
        default='states', help='Destination streem channel')
    parser.add_argument('--db-name', '-db', dest='dbname', type=str, 
        default='hbdb.db', help='Heartbeat database name')
    parser.add_argument('--interval', '-i', dest='interval', type=int, 
        default=10, help='Time (in seconds) interval between hearbeats')
    parser.add_argument('--timeout', '-t', dest='timeout', type=int, 
        default=60, help='Max allowed time (in seconds) interval between probe messages')
    return parser

#-----------------------------------------------------------------------------
# Checks if given timestamp has timed out
def timeout_exceeded(value, timeout):
    timestamp = time.time()
    if timestamp - value > timeout:
        return True
    else:
        return False

#-----------------------------------------------------------------------------

# Parse arguments
parser = create_parser()
args = parser.parse_args()

try:
    # Open database
    db = bsddb.hashopen(args.dbname, 'w')

    # Streem initialization
    conn = streem.Streem(args.host, args.port)
    conn.register(args.channel)
    
    while True:
        for key in db.keys():
            if timeout_exceeded(int(db[key]), args.timeout):
                json_message = json.loads(key)
                message = panopticon.message.Message(
                    aspect = json_message["event"]["name"],
                    location = json_message["location"],
                    state = "down",
                    severity = "error",
                )
                conn.submit(message.to_dict())
                del db[key]
                db.sync()
        time.sleep(args.interval)

except streem.ProtocolError as e:
    print "Streem returned status %s." % e.args
except KeyboardInterrupt:
    pass
finally:
    db.close()
