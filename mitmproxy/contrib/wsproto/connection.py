# -*- coding: utf-8 -*-
"""
wsproto/connection
~~~~~~~~~~~~~~

An implementation of a WebSocket connection.
"""

import os
import base64
import hashlib
from collections import deque

from enum import Enum

import h11

from .events import (
    ConnectionRequested, ConnectionEstablished, ConnectionClosed,
    ConnectionFailed, TextReceived, BytesReceived, PingReceived, PongReceived
)
from .frame_protocol import FrameProtocol, ParseFailed, CloseReason, Opcode


# RFC6455, Section 1.3 - Opening Handshake
ACCEPT_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class ConnectionState(Enum):
    """
    RFC 6455, Section 4 - Opening Handshake
    """
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3


class ConnectionType(Enum):
    CLIENT = 1
    SERVER = 2


CLIENT = ConnectionType.CLIENT
SERVER = ConnectionType.SERVER


# Some convenience utilities for working with HTTP headers
def _normed_header_dict(h11_headers):
    # This mangles Set-Cookie headers. But it happens that we don't care about
    # any of those, so it's OK. For every other HTTP header, if there are
    # multiple instances then you're allowed to join them together with
    # commas.
    name_to_values = {}
    for name, value in h11_headers:
        name_to_values.setdefault(name, []).append(value)
    name_to_normed_value = {}
    for name, values in name_to_values.items():
        name_to_normed_value[name] = b", ".join(values)
    return name_to_normed_value


# We use this for parsing the proposed protocol list, and for parsing the
# proposed and accepted extension lists. For the proposed protocol list it's
# fine, because the ABNF is just 1#token. But for the extension lists, it's
# wrong, because those can contain quoted strings, which can in turn contain
# commas. XX FIXME
def _split_comma_header(value):
    return [piece.decode('ascii').strip() for piece in value.split(b',')]


class WSConnection(object):
    """
    A low-level WebSocket connection object.

    This wraps two other protocol objects, an HTTP/1.1 protocol object used
    to do the initial HTTP upgrade handshake and a WebSocket frame protocol
    object used to exchange messages and other control frames.

    :param conn_type: Whether this object is on the client- or server-side of
        a connection. To initialise as a client pass ``CLIENT`` otherwise
        pass ``SERVER``.
    :type conn_type: ``ConnectionType``

    :param host: The hostname to pass to the server when acting as a client.
    :type host: ``str``

    :param resource: The resource (aka path) to pass to the server when acting
        as a client.
    :type resource: ``str``

    :param extensions: A list of  extensions to use on this connection.
        Extensions should be instances of a subclass of
        :class:`Extension <wsproto.extensions.Extension>`.

    :param subprotocols: A list of subprotocols to request when acting as a
        client, ordered by preference. This has no impact on the connection
        itself.
    :type subprotocol: ``list`` of ``str``
    """

    def __init__(self, conn_type, host=None, resource=None, extensions=None,
                 subprotocols=None):
        self.client = conn_type is ConnectionType.CLIENT

        self.host = host
        self.resource = resource

        self.subprotocols = subprotocols or []
        self.extensions = extensions or []

        self.version = b'13'

        self._state = ConnectionState.CONNECTING
        self._close_reason = None

        self._nonce = None
        self._outgoing = b''
        self._events = deque()
        self._proto = None

        if self.client:
            self._upgrade_connection = h11.Connection(h11.CLIENT)
        else:
            self._upgrade_connection = h11.Connection(h11.SERVER)

        if self.client:
            if self.host is None:
                raise ValueError(
                    "Host must not be None for a client-side connection.")
            if self.resource is None:
                raise ValueError(
                    "Resource must not be None for a client-side connection.")
            self.initiate_connection()

    def initiate_connection(self):
        self._generate_nonce()

        headers = {
            b"Host": self.host.encode('ascii'),
            b"Upgrade": b'WebSocket',
            b"Connection": b'Upgrade',
            b"Sec-WebSocket-Key": self._nonce,
            b"Sec-WebSocket-Version": self.version,
        }

        if self.subprotocols:
            headers[b"Sec-WebSocket-Protocol"] = ", ".join(self.subprotocols)

        if self.extensions:
            offers = {e.name: e.offer(self) for e in self.extensions}
            extensions = []
            for name, params in offers.items():
                if params is True:
                    extensions.append(name.encode('ascii'))
                elif params:
                    # py34 annoyance: doesn't support bytestring formatting
                    extensions.append(('%s; %s' % (name, params))
                                      .encode("ascii"))
            if extensions:
                headers[b'Sec-WebSocket-Extensions'] = b', '.join(extensions)

        upgrade = h11.Request(method=b'GET', target=self.resource,
                              headers=headers.items())
        self._outgoing += self._upgrade_connection.send(upgrade)

    def send_data(self, payload, final=True):
        """
        Send a message or part of a message to the remote peer.

        If ``final`` is ``False`` it indicates that this is part of a longer
        message. If ``final`` is ``True`` it indicates that this is either a
        self-contained message or the last part of a longer message.

        If ``payload`` is of type ``bytes`` then the message is flagged as
        being binary If it is of type ``str`` encoded as UTF-8 and sent as
        text.

        :param payload: The message body to send.
        :type payload: ``bytes`` or ``str``

        :param final: Whether there are more parts to this message to be sent.
        :type final: ``bool``
        """

        self._outgoing += self._proto.send_data(payload, final)

    def close(self, code=CloseReason.NORMAL_CLOSURE, reason=None):
        self._outgoing += self._proto.close(code, reason)
        self._state = ConnectionState.CLOSING

    @property
    def closed(self):
        return self._state is ConnectionState.CLOSED

    def bytes_to_send(self, amount=None):
        """
        Return any data that is to be sent to the remote peer.

        :param amount: (optional) The maximum number of bytes to be provided.
            If ``None`` or not provided it will return all available bytes.
        :type amount: ``int``
        """

        if amount is None:
            data = self._outgoing
            self._outgoing = b''
        else:
            data = self._outgoing[:amount]
            self._outgoing = self._outgoing[amount:]

        return data

    def receive_bytes(self, data):
        """
        Pass some received bytes to the connection for processing.

        :param data: The data received from the remote peer.
        :type data: ``bytes``
        """

        if data is None and self._state is ConnectionState.OPEN:
            # "If _The WebSocket Connection is Closed_ and no Close control
            # frame was received by the endpoint (such as could occur if the
            # underlying transport connection is lost), _The WebSocket
            # Connection Close Code_ is considered to be 1006."
            self._events.append(ConnectionClosed(CloseReason.ABNORMAL_CLOSURE))
            self._state = ConnectionState.CLOSED
            return
        elif data is None:
            self._state = ConnectionState.CLOSED
            return

        if self._state is ConnectionState.CONNECTING:
            event, data = self._process_upgrade(data)
            if event is not None:
                self._events.append(event)

        if self._state is ConnectionState.OPEN:
            self._proto.receive_bytes(data)

    def _process_upgrade(self, data):
        self._upgrade_connection.receive_data(data)
        while True:
            try:
                event = self._upgrade_connection.next_event()
            except h11.RemoteProtocolError:
                return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                        "Bad HTTP message"), b''
            if event is h11.NEED_DATA:
                break
            elif self.client and isinstance(event, (h11.InformationalResponse,
                                                    h11.Response)):
                data = self._upgrade_connection.trailing_data[0]
                return self._establish_client_connection(event), data
            elif not self.client and isinstance(event, h11.Request):
                return self._process_connection_request(event), None
            else:
                return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                        "Bad HTTP message"), b''

        self._incoming = b''
        return None, None

    def events(self):
        """
        Return a generator that provides any events that have been generated
        by protocol activity.

        :returns: generator
        """

        while self._events:
            yield self._events.popleft()

        if self._proto is None:
            return

        try:
            for frame in self._proto.received_frames():
                if frame.opcode is Opcode.PING:
                    assert frame.frame_finished and frame.message_finished
                    self._outgoing += self._proto.pong(frame.payload)
                    yield PingReceived(frame.payload)

                elif frame.opcode is Opcode.PONG:
                    assert frame.frame_finished and frame.message_finished
                    yield PongReceived(frame.payload)

                elif frame.opcode is Opcode.CLOSE:
                    code, reason = frame.payload
                    self.close(code, reason)
                    yield ConnectionClosed(code, reason)

                elif frame.opcode is Opcode.TEXT:
                    yield TextReceived(frame.payload,
                                       frame.frame_finished,
                                       frame.message_finished)

                elif frame.opcode is Opcode.BINARY:
                    yield BytesReceived(frame.payload,
                                        frame.frame_finished,
                                        frame.message_finished)
        except ParseFailed as exc:
            # XX FIXME: apparently autobahn intentionally deviates from the
            # spec in that on protocol errors it just closes the connection
            # rather than trying to send a CLOSE frame. Investigate whether we
            # should do the same.
            self.close(code=exc.code, reason=str(exc))
            yield ConnectionClosed(exc.code, reason=str(exc))

    def _generate_nonce(self):
        # os.urandom may be overkill for this use case, but I don't think this
        # is a bottleneck, and better safe than sorry...
        self._nonce = base64.b64encode(os.urandom(16))

    def _generate_accept_token(self, token):
        accept_token = token + ACCEPT_GUID
        accept_token = hashlib.sha1(accept_token).digest()
        return base64.b64encode(accept_token)

    def _establish_client_connection(self, event):
        if event.status_code != 101:
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Bad status code from server")
        headers = _normed_header_dict(event.headers)
        if headers[b'connection'].lower() != b'upgrade':
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Missing Connection: Upgrade header")
        if headers[b'upgrade'].lower() != b'websocket':
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Missing Upgrade: WebSocket header")

        accept_token = self._generate_accept_token(self._nonce)
        if headers[b'sec-websocket-accept'] != accept_token:
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Bad accept token")

        subprotocol = headers.get(b'sec-websocket-protocol', None)
        if subprotocol is not None:
            subprotocol = subprotocol.decode('ascii')
            if subprotocol not in self.subprotocols:
                return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                        "unrecognized subprotocol {!r}"
                                        .format(subprotocol))

        extensions = headers.get(b'sec-websocket-extensions', None)
        if extensions:
            accepts = _split_comma_header(extensions)

            for accept in accepts:
                name = accept.split(';', 1)[0].strip()
                for extension in self.extensions:
                    if extension.name == name:
                        extension.finalize(self, accept)
                        break
                else:
                    return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                            "unrecognized extension {!r}"
                                            .format(name))

        self._proto = FrameProtocol(self.client, self.extensions)
        self._state = ConnectionState.OPEN
        return ConnectionEstablished(subprotocol, extensions)

    def _process_connection_request(self, event):
        if event.method != b'GET':
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Request method must be GET")
        headers = _normed_header_dict(event.headers)
        if headers[b'connection'].lower() != b'upgrade':
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Missing Connection: Upgrade header")
        if headers[b'upgrade'].lower() != b'websocket':
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Missing Upgrade: WebSocket header")

        if b'sec-websocket-version' not in headers:
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Missing Sec-WebSocket-Version header")
        # XX FIXME: need to check Sec-Websocket-Version, and respond with a
        # 400 if it's not what we expect

        if b'sec-websocket-protocol' in headers:
            proposed_subprotocols = _split_comma_header(
                headers[b'sec-websocket-protocol'])
        else:
            proposed_subprotocols = []

        if b'sec-websocket-key' not in headers:
            return ConnectionFailed(CloseReason.PROTOCOL_ERROR,
                                    "Missing Sec-WebSocket-Key header")

        return ConnectionRequested(proposed_subprotocols, event)

    def _extension_accept(self, extensions_header):
        accepts = {}
        offers = _split_comma_header(extensions_header)

        for offer in offers:
            name = offer.split(';', 1)[0].strip()
            for extension in self.extensions:
                if extension.name == name:
                    accept = extension.accept(self, offer)
                    if accept is True:
                        accepts[extension.name] = True
                    elif accept is not False and accept is not None:
                        accepts[extension.name] = accept.encode('ascii')

        if accepts:
            extensions = []
            for name, params in accepts.items():
                if params is True:
                    extensions.append(name.encode('ascii'))
                else:
                    # py34 annoyance: doesn't support bytestring formatting
                    params = params.decode("ascii")
                    extensions.append(('%s; %s' % (name, params))
                                      .encode("ascii"))
            return b', '.join(extensions)

        return None

    def accept(self, event, subprotocol=None):
        request = event.h11request
        request_headers = _normed_header_dict(request.headers)

        nonce = request_headers[b'sec-websocket-key']
        accept_token = self._generate_accept_token(nonce)

        headers = {
            b"Upgrade": b'WebSocket',
            b"Connection": b'Upgrade',
            b"Sec-WebSocket-Accept": accept_token,
        }

        if subprotocol is not None:
            if subprotocol not in event.proposed_subprotocols:
                raise ValueError(
                    "unexpected subprotocol {!r}".format(subprotocol))
            headers[b'Sec-WebSocket-Protocol'] = subprotocol

        extensions = request_headers.get(b'sec-websocket-extensions', None)
        if extensions:
            accepts = self._extension_accept(extensions)
            if accepts:
                headers[b"Sec-WebSocket-Extensions"] = accepts

        response = h11.InformationalResponse(status_code=101,
                                             headers=headers.items())
        self._outgoing += self._upgrade_connection.send(response)
        self._proto = FrameProtocol(self.client, self.extensions)
        self._state = ConnectionState.OPEN

    def ping(self, payload=None):
        """
        Send a PING message to the peer.

        :param payload: an optional payload to send with the message
        """

        payload = bytes(payload or b'')
        self._outgoing += self._proto.ping(payload)

    def pong(self, payload=None):
        """
        Send a PONG message to the peer.

        This method can be used to send an unsolicted PONG to the peer.
        It is not needed otherwise since every received PING causes a
        corresponding PONG to be sent automatically.

        :param payload: an optional payload to send with the message
        """

        payload = bytes(payload or b'')
        self._outgoing += self._proto.pong(payload)
