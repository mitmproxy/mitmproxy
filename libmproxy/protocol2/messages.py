"""
This module contains all valid messages layers can send to the underlying layers.
"""
from __future__ import (absolute_import, print_function, division)
from netlib.tcp import Address


class _Message(object):
    def __eq__(self, other):
        # Allow message == Connect checks.
        if isinstance(self, other):
            return True
        return self is other

    def __ne__(self, other):
        return not self.__eq__(other)


class Connect(_Message):
    """
    Connect to the server
    """


class Reconnect(_Message):
    """
    Re-establish the server connection
    """


class SetServer(_Message):
    """
    Change the upstream server.
    """

    def __init__(self, address, server_tls, sni, depth=1):
        self.address = Address.wrap(address)
        self.server_tls = server_tls
        self.sni = sni

        # upstream proxy scenario: you may want to change either the final target or the upstream proxy.
        # We can express this neatly as the "nth-server-providing-layer"
        # ServerConnection could get a `via` attribute.
        self.depth = depth


class Kill(_Message):
    """
    Kill a connection.
    """