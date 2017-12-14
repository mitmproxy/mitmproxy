# -*- coding: utf-8 -*-
"""
wsproto/events
~~~~~~~~~~

Events that result from processing data on a WebSocket connection.
"""


class ConnectionRequested(object):
    def __init__(self, proposed_subprotocols, h11request):
        self.proposed_subprotocols = proposed_subprotocols
        self.h11request = h11request

    def __repr__(self):
        path = self.h11request.target

        headers = dict(self.h11request.headers)
        host = headers[b'host']
        version = headers[b'sec-websocket-version']
        subprotocol = headers.get(b'sec-websocket-protocol', None)
        extensions = []

        fmt = '<%s host=%s path=%s version=%s subprotocol=%r extensions=%r>'
        return fmt % (self.__class__.__name__, host, path, version,
                      subprotocol, extensions)


class ConnectionEstablished(object):
    def __init__(self, subprotocol=None, extensions=None):
        self.subprotocol = subprotocol
        self.extensions = extensions
        if self.extensions is None:
            self.extensions = []

    def __repr__(self):
        return '<ConnectionEstablished subprotocol=%r extensions=%r>' % \
               (self.subprotocol, self.extensions)


class ConnectionClosed(object):
    def __init__(self, code, reason=None):
        self.code = code
        self.reason = reason

    def __repr__(self):
        return '<%s code=%r reason="%s">' % (self.__class__.__name__,
                                             self.code, self.reason)


class ConnectionFailed(ConnectionClosed):
    pass


class DataReceived(object):
    def __init__(self, data, frame_finished, message_finished):
        self.data = data
        # This has no semantic content, but is provided just in case some
        # weird edge case user wants to be able to reconstruct the
        # fragmentation pattern of the original stream. You don't want it:
        self.frame_finished = frame_finished
        # This is the field that you almost certainly want:
        self.message_finished = message_finished


class TextReceived(DataReceived):
    pass


class BytesReceived(DataReceived):
    pass


class PingReceived(object):
    def __init__(self, payload):
        self.payload = payload


class PongReceived(object):
    def __init__(self, payload):
        self.payload = payload
