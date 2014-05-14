******************
Panopticon message
******************

Examples of use
---------------

Creating a new message
^^^^^^^^^^^^^^^^^^^^^^

Very basic message carrying just a single value::

   from panopticon.message import Message

   msg = Message(
       aspect = "users logged in",
       location = { "host": os.uname()[1] },
       value = 200,
   )
   print json.dumps(msg.to_dict(), sort_keys = True)

Message about Apache not working::

   from panopticon.message import Message

   msg = Message(
       aspect = "process state",
       location = { "host": os.uname()[1], "service": "apache" },
       state = "down", severity = "error",
   )
   print json.dumps(msg.to_dict(), sort_keys = True)


More verbose message carrying information about disk space on :file:`/`::

   from panopticon.message import Message, Value

   msg = Message(
       aspect = "disk space",
       location = { "host": os.uname()[1], "filesystem": "/" },
   )
   # set value and thresholds at the same time
   msg["free"] = Value(200, unit = "MB") \
                     .set_below(512, "warning", "warning") \
                     .set_below(256, "critical", "error")
   # value can be set with integer
   msg["total"] = 1024
   # value can be updated
   msg["total"].unit = msg["free"].unit

   print json.dumps(msg.to_dict(), sort_keys = True)


Altering an incoming message
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace *total* + *free* with *used* + *free* in message about disk space::

   from panopticon.message import Message

   # pretend that this artificial message came from outside
   incoming = {
       "v": 3,
       "time": int(time.time()),
       "location": { "host": os.uname()[1], "filesystem": "/" },
       "event": {
           "name": "disk space",
           "vset": { "free": { "value": 200 }, "total": { "value": 1024 } }
       }
   }

   msg = Message(message = incoming)
   msg["used"] = int(msg["total"]) - int(msg["free"])
   # alternatively:
   #msg["used"] = msg["total"].value - msg["free"].value
   del msg["total"]

   print json.dumps(msg.to_dict(), sort_keys = True)

Add a location to a message::

   from panopticon.message import Message

   # pretend that this artificial message came from outside
   incoming = {
       "v": 3,
       "time": int(time.time()),
       "location": { "host": os.uname()[1] },
       "event": {
           "name": "disk space",
           "vset": { "free": { "value": 200 }, "total": { "value": 1024 } }
       }
   }

   msg = Message(message = incoming)
   msg.location["filesystem"] = "/"

   print json.dumps(msg.to_dict(), sort_keys = True)


Checking a message for exceeding thresholds
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   from panopticon.message import Message, Value

   msg1 = Message(
       aspect = "dummy",
       location = { "host": os.uname()[1], "item": "1" },
       value = Value(100).set_above(200, "error"),
   )
   msg2 = Message(
       aspect = "dummy",
       location = { "host": os.uname()[1], "item": "2" },
       value = Value(202).set_above(200, "error"),
   )

   # simple check on all there is in msg1
   result = msg1.exceeds()
   if result is None:
       print "msg1 in norm"
   else:
       print "msg1 exceeds %s (severity %s)" % (result[0], result[1])

   # check for exceeding high thresholds, value "value" only
   result = msg2['value'].is_above()
   if result is None:
       print "msg2 in norm"
   else:
       print "msg2 > %s (severity %s)" % (result[0], result[1])

   # check against hardcoded threshold
   if msg2['value'] <= 100:
       print "msg2[value] doesn't exceed threshold (or is None)"
   else:
       print "msg2[value] > 100"

   # check if the value is set
   if msg2['value'] == None:
       print "msg2[value] is unset"


API documentation
-----------------

.. automodule:: panopticon.message

