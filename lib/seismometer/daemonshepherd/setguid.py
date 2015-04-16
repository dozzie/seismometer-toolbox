#!/usr/bin/python
'''
Set UID and GID of process
--------------------------

.. autofunction:: setguid

'''
#-----------------------------------------------------------------------------

import os
import pwd
import grp

#-----------------------------------------------------------------------------

def setguid(user, group):
    '''
    :param user: username to change UID to
    :param group: group name to change GID to

    Set UID and GID of current process.
    '''
    uid = None
    gid = None

    if user is not None:
        pw_user = pwd.getpwnam(user)
        uid = pw_user.pw_uid
        gid = pw_user.pw_gid # will be replaced if group was specified

    if group is not None:
        gr_group = grp.getgrnam(group)
        gid = gr_group.gr_gid

    # after UID change it may be impossible to change primary group
    if gid is not None:
        os.setgid(gid)
    if uid is not None:
        os.setuid(uid)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
