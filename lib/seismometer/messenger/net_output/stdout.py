#!/usr/bin/python
'''
STDOUT message writer.

.. autoclass:: STDOUT
   :members:

'''
#-----------------------------------------------------------------------------

import sys
import json

#-----------------------------------------------------------------------------

class STDOUT:
    '''
    Sender printing message to STDOUT.
    '''
    def __init__(self):
        pass

    def send(self, message):
        line = json.dumps(message) + '\n'
        sys.stdout.write(line)
        sys.stdout.flush()

    def flush(self):
        pass

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
