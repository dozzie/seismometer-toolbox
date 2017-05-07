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
    result["free"] = Value(
        stat.f_bfree  * stat.f_bsize / 1024.0 / 1024.0,
        unit = "MB",
    )
    result["total"] = Value(
        stat.f_blocks * stat.f_bsize / 1024.0 / 1024.0,
        unit = "MB",
    )
    return result

def parse_iostat(line):
    if not line.startswith("sd") and not line.startswith("dm-"):
        return ()
    (device, tps, rspeed, wspeed, rbytes, wbytes) = line.split()
    result = Message(
        aspect = "disk I/O",
        location = {
            "host": hostname(),
            "device": device,
        },
    )
    result["read_speed"] = Value(float(rspeed), unit = "kB/s")
    result["write_speed"] = Value(float(wspeed), unit = "kB/s")
    result["transactions"] = Value(float(tps), unit = "tps")
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
    ShellCommand(
        "/usr/local/bin/read-etc-passwd",
        parse = lambda stdout,code: [
            json.loads(l) for l in stdout.strip().split("\n")
        ],
        interval = 60
    ),
    # external command (run without `sh -c'), prints single number
    ShellCommand(
        ["/usr/local/bin/random", "0.5"],
        parse = lambda stdout,code: Message(
          aspect = "random",
          value = float(stdout),
        ),
        interval = 30,
        host = hostname(),
    ),
    # and two Monitoring Plugins
    Nagios(
        # this one runs without shell
        ["/usr/lib/nagios/plugins/check_load", "-w", "0.25", "-c", "0.5"],
        interval = 10,
        aspect = "load average",
        host = hostname(), service = "load",
    ),
    Nagios(
        # this one runs with shell
        "/usr/lib/nagios/plugins/check_users -w 3 -c 5",
        interval = 60,
        aspect = "wtmp",
        host = hostname(), service = "users",
    ),
    # spawn iostat(1), make it print statistics every 20s, and make them
    # proper Seismometer messages
    ShellStream(["/usr/bin/iostat", "-p", "20"], parse = parse_iostat),
]

#--------------------------------------------------------------------------
# vim:ft=python
