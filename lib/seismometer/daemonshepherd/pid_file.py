#!/usr/bin/python
'''
Managing pid file
-----------------

.. autoclass:: PidFile
   :members:

'''
#-----------------------------------------------------------------------------

import os

#-----------------------------------------------------------------------------

class PidFile:
    '''
    Handle for pid file. The file will be deleted when the instance is
    destroyed, if the file ownership was claimed (see :meth:`claim()`).
    '''

    def __init__(self, filename):
        '''
        :param filename: name of the pid file
        :type filename: string
        '''
        self.filename = os.path.abspath(filename)
        self.fd = open(self.filename, 'w', 0) # TODO: atomic create-or-fail
        self.pid = None
        self.remove_on_close = False
        self.update()

    def claim(self):
        '''
        Claim the ownership of the pid file. Owner process is responsible for
        removing it at the end.
        '''
        self.remove_on_close = True

    def update(self):
        '''
        Update content of pid file with current process' PID.
        '''
        if self.fd is None:
            return # or raise an error?
        self.pid = os.getpid()
        self.fd.seek(0)
        self.fd.write("%d\n" % (self.pid))
        self.fd.truncate()

    def close(self):
        '''
        Close pid file *without* removing it.
        '''
        self.fd.close()
        self.fd = None

    def __del__(self):
        if self.fd is None:
            # do nothing if closed already
            return

        self.fd.close()
        if self.remove_on_close and self.pid == os.getpid():
            # only remove the file if owner
            os.unlink(self.filename)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
