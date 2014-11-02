#!/usr/bin/python
'''
DumbProbe config interface
--------------------------

This interface is intended for use in script specified with :option:`--checks`
option.

.. autoclass:: Checks
   :members:

.. autoclass:: ShellCommand
   :members:

'''
#-----------------------------------------------------------------------------

from shell_command import ShellCommand
from service import Checks

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
