"""
This module contains the proxy layers for raw QUIC proxying.
This is used if we want to speak QUIC, but we do not want to do HTTP.
"""

from __future__ import annotations

import time

from aioquic.quic.connection import QuicErrorCode
from aioquic.quic.connection import stream_is_client_initiated
from aioquic.quic.connection import stream_is_unidirectional

from ._commands import CloseQuicConnection
from ._commands import ResetQuicStream
from ._commands import SendQuicStreamData
from ._commands import StopSendingQuicStream
from ._events import QuicConnectionClosed
from ._events import QuicStreamDataReceived
from ._events import QuicStreamEvent
from ._events import QuicStreamReset
from mitmproxy import connection
from mitmproxy.connection import Connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy import tunnel
from mitmproxy.proxy.layers.tcp import TCPLayer
from mitmproxy.proxy.layers.udp import UDPLayer


class QuicStreamNextLayer(layer.NextLayer):
    """`NextLayer` variant that callbacks `QuicStreamLayer` after layer decision."""

    def __init__(
        self,
        context: context.Context,
        stream: QuicStreamLayer,
        ask_on_start: bool = False,
    ) -> None:
        super().__init__(context, ask_on_start)
        self._stream = stream
        self._layer: layer.Layer | None = None

    @property  # type: ignore
    def layer(self) -> layer.Layer | None:  # type: ignore
        return self._layer

    @layer.setter
    def layer(self, value: layer.Layer | None) -> None:
        self._layer = value
        if self._layer:
            self._stream.refresh_metadata()


class QuicStreamLayer(layer.Layer):
    """
    Layer for QUIC streams.
    Serves as a marker for NextLayer and keeps track of the connection states.
    """

    client: connection.Client
    """Virtual client connection for this stream. Use this in QuicRawLayer instead of `context.client`."""
    server: connection.Server
    """Virtual server connection for this stream. Use this in QuicRawLayer instead of `context.server`."""
    child_layer: layer.Layer
    """The stream's child layer."""

    def __init__(
        self, context: context.Context, force_raw: bool, stream_id: int
    ) -> None:
        # we mustn't reuse the client from the QUIC connection, as the state and protocol differs
        self.client = context.client = context.client.copy()
        self.client.transport_protocol = "tcp"
        self.client.state = connection.ConnectionState.OPEN

        # unidirectional client streams are not fully open, set the appropriate state
        if stream_is_unidirectional(stream_id):
            self.client.state = (
                connection.ConnectionState.CAN_READ
                if stream_is_client_initiated(stream_id)
                else connection.ConnectionState.CAN_WRITE
            )
        self._client_stream_id = stream_id

        # start with a closed server
        self.server = context.server = connection.Server(
            address=context.server.address,
            transport_protocol="tcp",
        )
        self._server_stream_id: int | None = None

        super().__init__(context)
        self.child_layer = (
            TCPLayer(context) if force_raw else QuicStreamNextLayer(context, self)
        )
        self.refresh_metadata()

        # we don't handle any events, pass everything to the child layer
        self.handle_event = self.child_layer.handle_event  # type: ignore
        self._handle_event = self.child_layer._handle_event  # type: ignore

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        raise AssertionError  # pragma: no cover

    def open_server_stream(self, server_stream_id) -> None:
        assert self._server_stream_id is None
        self._server_stream_id = server_stream_id
        self.server.timestamp_start = time.time()
        self.server.state = (
            (
                connection.ConnectionState.CAN_WRITE
                if stream_is_client_initiated(server_stream_id)
                else connection.ConnectionState.CAN_READ
            )
            if stream_is_unidirectional(server_stream_id)
            else connection.ConnectionState.OPEN
        )
        self.refresh_metadata()

    def refresh_metadata(self) -> None:
        # find the first transport layer
        child_layer: layer.Layer | None = self.child_layer
        while True:
            if isinstance(child_layer, layer.NextLayer):
                child_layer = child_layer.layer
            elif isinstance(child_layer, tunnel.TunnelLayer):
                child_layer = child_layer.child_layer
            else:
                break  # pragma: no cover
        if isinstance(child_layer, (UDPLayer, TCPLayer)) and child_layer.flow:
            child_layer.flow.metadata["quic_is_unidirectional"] = (
                stream_is_unidirectional(self._client_stream_id)
            )
            child_layer.flow.metadata["quic_initiator"] = (
                "client"
                if stream_is_client_initiated(self._client_stream_id)
                else "server"
            )
            child_layer.flow.metadata["quic_stream_id_client"] = self._client_stream_id
            child_layer.flow.metadata["quic_stream_id_server"] = self._server_stream_id

    def stream_id(self, client: bool) -> int | None:
        return self._client_stream_id if client else self._server_stream_id


class RawQuicLayer(layer.Layer):
    """
    This layer is responsible for de-multiplexing QUIC streams into an individual layer stack per stream.
    """

    force_raw: bool
    """Indicates whether traffic should be treated as raw TCP/UDP without further protocol detection."""
    datagram_layer: layer.Layer
    """
  The layer that is handling datagrams over QUIC. It's like a child_layer, but with a forked context.
  Instead of having a datagram-equivalent for all `QuicStream*` classes, we use `SendData` and `DataReceived` instead.
  There is also no need for another `NextLayer` marker, as a missing `QuicStreamLayer` implies UDP,
  and the connection state is the same as the one of the underlying QUIC connection.
  """
    client_stream_ids: dict[int, QuicStreamLayer]
    """Maps stream IDs from the client connection to stream layers."""
    server_stream_ids: dict[int, QuicStreamLayer]
    """Maps stream IDs from the server connection to stream layers."""
    connections: dict[connection.Connection, layer.Layer]
    """Maps connections to layers."""
    command_sources: dict[commands.Command, layer.Layer]
    """Keeps track of blocking commands and wakeup requests."""
    next_stream_id: list[int]
    """List containing the next stream ID for all four is_unidirectional/is_client combinations."""

    def __init__(self, context: context.Context, force_raw: bool = False) -> None:
        super().__init__(context)
        self.force_raw = force_raw
        self.datagram_layer = (
            UDPLayer(self.context.fork())
            if force_raw
            else layer.NextLayer(self.context.fork())
        )
        self.client_stream_ids = {}
        self.server_stream_ids = {}
        self.connections = {
            context.client: self.datagram_layer,
            context.server: self.datagram_layer,
        }
        self.command_sources = {}
        self.next_stream_id = [0, 1, 2, 3]

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        # we treat the datagram layer as child layer, so forward Start
        if isinstance(event, events.Start):
            if self.context.server.timestamp_start is None:
                err = yield commands.OpenConnection(self.context.server)
                if err:
                    yield commands.CloseConnection(self.context.client)
                    self._handle_event = self.done  # type: ignore
                    return
            yield from self.event_to_child(self.datagram_layer, event)

        # properly forward completion events based on their command
        elif isinstance(event, events.CommandCompleted):
            yield from self.event_to_child(
                self.command_sources.pop(event.command), event
            )

        # route injected messages based on their connections (prefer client, fallback to server)
        elif isinstance(event, events.MessageInjected):
            if event.flow.client_conn in self.connections:
                yield from self.event_to_child(
                    self.connections[event.flow.client_conn], event
                )
            elif event.flow.server_conn in self.connections:
                yield from self.event_to_child(
                    self.connections[event.flow.server_conn], event
                )
            else:
                raise AssertionError(f"Flow not associated: {event.flow!r}")

        # handle stream events targeting this context
        elif isinstance(event, QuicStreamEvent) and (
            event.connection is self.context.client
            or event.connection is self.context.server
        ):
            from_client = event.connection is self.context.client

            # fetch or create the layer
            stream_ids = (
                self.client_stream_ids if from_client else self.server_stream_ids
            )
            if event.stream_id in stream_ids:
                stream_layer = stream_ids[event.stream_id]
            else:
                # ensure we haven't just forgotten to register the ID
                assert stream_is_client_initiated(event.stream_id) == from_client

                # for server-initiated streams we need to open the client as well
                if from_client:
                    client_stream_id = event.stream_id
                    server_stream_id = None
                else:
                    client_stream_id = self.get_next_available_stream_id(
                        is_client=False,
                        is_unidirectional=stream_is_unidirectional(event.stream_id),
                    )
                    server_stream_id = event.stream_id

                # create, register and start the layer
                stream_layer = QuicStreamLayer(
                    self.context.fork(),
                    force_raw=self.force_raw,
                    stream_id=client_stream_id,
                )
                self.client_stream_ids[client_stream_id] = stream_layer
                if server_stream_id is not None:
                    stream_layer.open_server_stream(server_stream_id)
                    self.server_stream_ids[server_stream_id] = stream_layer
                self.connections[stream_layer.client] = stream_layer
                self.connections[stream_layer.server] = stream_layer
                yield from self.event_to_child(stream_layer, events.Start())

            # forward data and close events
            conn: Connection = (
                stream_layer.client if from_client else stream_layer.server
            )
            if isinstance(event, QuicStreamDataReceived):
                if event.data:
                    yield from self.event_to_child(
                        stream_layer, events.DataReceived(conn, event.data)
                    )
                if event.end_stream:
                    yield from self.close_stream_layer(stream_layer, from_client)
            elif isinstance(event, QuicStreamReset):
                # preserve stream resets
                for command in self.close_stream_layer(stream_layer, from_client):
                    if (
                        isinstance(command, SendQuicStreamData)
                        and command.stream_id == stream_layer.stream_id(not from_client)
                        and command.end_stream
                        and not command.data
                    ):
                        yield ResetQuicStream(
                            command.connection, command.stream_id, event.error_code
                        )
                    else:
                        yield command
            else:
                raise AssertionError(f"Unexpected stream event: {event!r}")

        # handle close events that target this context
        elif isinstance(event, QuicConnectionClosed) and (
            event.connection is self.context.client
            or event.connection is self.context.server
        ):
            from_client = event.connection is self.context.client
            other_conn = self.context.server if from_client else self.context.client

            # be done if both connections are closed
            if other_conn.connected:
                yield CloseQuicConnection(
                    other_conn, event.error_code, event.frame_type, event.reason_phrase
                )
            else:
                self._handle_event = self.done  # type: ignore

            # always forward to the datagram layer and swallow `CloseConnection` commands
            for command in self.event_to_child(self.datagram_layer, event):
                if (
                    not isinstance(command, commands.CloseConnection)
                    or command.connection is not other_conn
                ):
                    yield command

            # forward to either the client or server connection of stream layers and swallow empty stream end
            for conn, child_layer in self.connections.items():
                if isinstance(child_layer, QuicStreamLayer) and (
                    (conn is child_layer.client)
                    if from_client
                    else (conn is child_layer.server)
                ):
                    conn.state &= ~connection.ConnectionState.CAN_WRITE
                    for command in self.close_stream_layer(child_layer, from_client):
                        if not isinstance(command, SendQuicStreamData) or command.data:
                            yield command

        # all other connection events are routed to their corresponding layer
        elif isinstance(event, events.ConnectionEvent):
            yield from self.event_to_child(self.connections[event.connection], event)

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def close_stream_layer(
        self, stream_layer: QuicStreamLayer, client: bool
    ) -> layer.CommandGenerator[None]:
        """Closes the incoming part of a connection."""

        conn = stream_layer.client if client else stream_layer.server
        conn.state &= ~connection.ConnectionState.CAN_READ
        assert conn.timestamp_start is not None
        if conn.timestamp_end is None:
            conn.timestamp_end = time.time()
            yield from self.event_to_child(stream_layer, events.ConnectionClosed(conn))

    def event_to_child(
        self, child_layer: layer.Layer, event: events.Event
    ) -> layer.CommandGenerator[None]:
        """Forwards events to child layers and translates commands."""

        for command in child_layer.handle_event(event):
            # intercept commands for streams connections
            if (
                isinstance(child_layer, QuicStreamLayer)
                and isinstance(command, commands.ConnectionCommand)
                and (
                    command.connection is child_layer.client
                    or command.connection is child_layer.server
                )
            ):
                # get the target connection and stream ID
                to_client = command.connection is child_layer.client
                quic_conn = self.context.client if to_client else self.context.server
                stream_id = child_layer.stream_id(to_client)

                # write data and check CloseConnection wasn't called before
                if isinstance(command, commands.SendData):
                    assert stream_id is not None
                    if command.connection.state & connection.ConnectionState.CAN_WRITE:
                        yield SendQuicStreamData(quic_conn, stream_id, command.data)

                # send a FIN and optionally also a STOP frame
                elif isinstance(command, commands.CloseConnection):
                    assert stream_id is not None
                    if command.connection.state & connection.ConnectionState.CAN_WRITE:
                        command.connection.state &= (
                            ~connection.ConnectionState.CAN_WRITE
                        )
                        yield SendQuicStreamData(
                            quic_conn, stream_id, b"", end_stream=True
                        )
                    # XXX: Use `command.connection.state & connection.ConnectionState.CAN_READ` instead?
                    only_close_our_half = (
                        isinstance(command, commands.CloseTcpConnection)
                        and command.half_close
                    )
                    if not only_close_our_half:
                        if stream_is_client_initiated(
                            stream_id
                        ) == to_client or not stream_is_unidirectional(stream_id):
                            yield StopSendingQuicStream(
                                quic_conn, stream_id, QuicErrorCode.NO_ERROR
                            )
                        yield from self.close_stream_layer(child_layer, to_client)

                # open server connections by reserving the next stream ID
                elif isinstance(command, commands.OpenConnection):
                    assert not to_client
                    assert stream_id is None
                    client_stream_id = child_layer.stream_id(client=True)
                    assert client_stream_id is not None
                    stream_id = self.get_next_available_stream_id(
                        is_client=True,
                        is_unidirectional=stream_is_unidirectional(client_stream_id),
                    )
                    child_layer.open_server_stream(stream_id)
                    self.server_stream_ids[stream_id] = child_layer
                    yield from self.event_to_child(
                        child_layer, events.OpenConnectionCompleted(command, None)
                    )

                else:
                    raise AssertionError(
                        f"Unexpected stream connection command: {command!r}"
                    )

            # remember blocking and wakeup commands
            else:
                if command.blocking or isinstance(command, commands.RequestWakeup):
                    self.command_sources[command] = child_layer
                if isinstance(command, commands.OpenConnection):
                    self.connections[command.connection] = child_layer
                yield command

    def get_next_available_stream_id(
        self, is_client: bool, is_unidirectional: bool = False
    ) -> int:
        index = (int(is_unidirectional) << 1) | int(not is_client)
        stream_id = self.next_stream_id[index]
        self.next_stream_id[index] = stream_id + 4
        return stream_id

    def done(self, _) -> layer.CommandGenerator[None]:  # pragma: no cover
        yield from ()
