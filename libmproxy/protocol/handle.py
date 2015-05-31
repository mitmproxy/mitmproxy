from __future__ import absolute_import
from . import http, tcp

protocols = {
    'http': dict(handler=http.HTTPHandler, flow=http.HTTPFlow),
    'tcp': dict(handler=tcp.TCPHandler)
}


def protocol_handler(protocol):
    """
    @type protocol: str
    @returns: libmproxy.protocol.primitives.ProtocolHandler
    """
    if protocol in protocols:
        return protocols[protocol]["handler"]

    raise NotImplementedError(
        "Unknown Protocol: %s" %
        protocol)   # pragma: nocover
