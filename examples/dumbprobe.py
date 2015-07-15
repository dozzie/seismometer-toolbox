#!/usr/bin/python

from seismometer.dumbprobe import *
from seismometer.message import Message, Value
import os

#--------------------------------------------------------------------------

def hostname():
    return os.uname()[1]

#--------------------------------------------------------------------------

def uptime():
    with open("/proc/uptime") as f:
        return Message(
            aspect = "uptime",
            location = {"host": hostname()},
            value = float(f.read().split()[0]),
        )

def df(mountpoint):
    stat = os.statvfs(mountpoint)
    result = Message(
        aspect = "disk space",
        location = {
            "host": hostname(),
            "filesystem": mountpoint,
        },
    )
    result["free"]  = Value(
        stat.f_bfree  * stat.f_bsize / 1024.0 / 1024.0,
        unit = "MB",
    )
    result["total"] = Value(
        stat.f_blocks * stat.f_bsize / 1024.0 / 1024.0,
        unit = "MB",
    )
    return result

#--------------------------------------------------------------------------

CHECKS = [
    # function called every 60s with empty arguments list
    Function(uptime, interval = 60),
    # function called every 30 minutes with a single argument
    Function(df, args = ["/"],     interval = 30 * 60),
    Function(df, args = ["/home"], interval = 30 * 60),
    Function(df, args = ["/tmp"],  interval = 30 * 60),
    # shell command (`sh -c ...'), prints list of JSON objects to STDOUT
    ShellOutputJSON("/usr/local/bin/read-etc-passwd", interval = 60),
    # external command (run without `sh -c'), prints single number
    ShellOutputMetric(
        ["/usr/local/bin/random", "0.5"],
        interval = 30,
        aspect = "random",
        host = hostname(),
    ),
    # external command, prints "missing" (expected) or anything else
    # (error)
    ShellOutputState(
        ["/usr/local/bin/file_exists", "/etc/nologin"],
        expected = ["missing"],
        interval = 60,
        aspect = "nologin marker",
    ),
    # and two Monitoring Plugins
    Nagios(
        # this one is run without shell
        ["/usr/lib/nagios/plugins/check_load", "-w", "0.25", "-c", "0.5"],
        interval = 10,
        aspect = "load average",
        host = hostname(), service = "load",
    ),
    Nagios(
        # this one is run with shell
        "/usr/lib/nagios/plugins/check_users -w 3 -c 5",
        interval = 60,
        aspect = "wtmp",
        host = hostname(), service = "users",
    ),
]

#--------------------------------------------------------------------------
# vim:ft=python
