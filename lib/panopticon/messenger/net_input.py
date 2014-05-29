#!/usr/bin/python

#-----------------------------------------------------------------------------

#   * socket aggregator (single poll(), returns one line at time)
#     * TCP sockets
#     * UDP sockets
#     * UNIX sockets (SOCK_DGRAM)
#     * hostname: for future: DNS cache; for now: IP address
#   * protocol parser
#     * JSON
#     * Graphite (tag value timestamp)
#     * Graphite-like (tag state severity timestamp)
#     * timestamp == "N" means now
#     * value == "U" means undefined
#     * drop non-conforming messages

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
