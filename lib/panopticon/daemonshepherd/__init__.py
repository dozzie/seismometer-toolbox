#!/usr/bin/python
'''
*daemonshepherd*'s main operations
----------------------------------

.. autoclass:: PidFile
   :members: update, claim

   This class is imported :class:`pid_file.PidFile`.

.. autoclass:: Controller
   :members: shutdown, loop

   This class is imported :class:`controller.Controller`.

.. autofunction:: setguid

   This function is imported :func:`setguid.setguid`.

.. autofunction:: detach

   This function is imported :func:`self_detach.detach`.

.. autofunction:: detach_succeeded

   This function is imported :func:`self_detach.detach_succeeded`.

'''
#-----------------------------------------------------------------------------

from pid_file import PidFile
from setguid import setguid
from self_detach import detach, detach_succeeded
from controller import Controller

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
