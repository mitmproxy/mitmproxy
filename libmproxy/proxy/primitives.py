from __future__ import absolute_import
import collections
from netlib import socks, tcp


class Log(object):
    def __init__(self, msg, level="info"):
        self.msg = msg
        self.level = level


class Kill(Exception):
    """
    Kill a connection.
    """