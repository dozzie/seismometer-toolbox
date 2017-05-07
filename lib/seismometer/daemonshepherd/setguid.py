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

def getguid(user):
    pw_user = pwd.getpwnam(user)
    return (pw_user.pw_uid, [pw_user.pw_gid])

def getgid(group):
    gr_group = grp.getgrnam(group)
    return gr_group.gr_gid

def setguid(user, group):
    '''
    :param user: username to change UID to
    :param group: group name (or list of group names) to change GID to

    Set UID and GID of current process. If :obj:`user` is ``None``, UID will
    not be changed. If :obj:`group` is ``None``, then GID will be set to the
    primary group of :obj:`user`. If both :obj:`user` and :obj:`group` are
    ``None``, neither UID nor GID will be changed.
    '''
    uid = None
    gids = None

    if isinstance(user, (str, unicode)):
        (uid, gids) = getguid(user)

    if isinstance(group, (str, unicode)):
        gids = [getgid(group)]
    elif isinstance(group, (list, tuple)):
        gids = [getgid(g) for g in group]

    # after UID change it may be impossible to change groups
    if gids is not None:
        os.setgid(gids[0])
        os.setgroups(gids)
    if uid is not None:
        os.setuid(uid)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
