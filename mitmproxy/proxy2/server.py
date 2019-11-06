"""
Proxy Server Implementation using asyncio.
The very high level overview is as follows:

    - Spawn one coroutine per client connection and create a reverse proxy layer to example.com
    - Process any commands from layer (such as opening a server connection)
    - Wait for any IO and send it as events to top layer.
"""
import abc
import asyncio
import logging
import socket
import sys
import traceback
import typing

from mitmproxy import http, options as moptions
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events, layer, layers
from mitmproxy.proxy2.context import Client, Connection, ConnectionState, Context
from mitmproxy.proxy2.layers import glue
from mitmproxy.utils import human


class StreamIO(typing.NamedTuple):
    r: asyncio.StreamReader
    w: asyncio.StreamWriter


class ConnectionHandler(metaclass=abc.ABCMeta):
    transports: typing.MutableMapping[Connection, StreamIO]

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, options: moptions.Options) -> None:
        addr = writer.get_extra_info('peername')

        self.client = Client(addr)
        self.context = Context(self.client, options)
        self.layer = layer.NextLayer(self.context)

        # Ask for the first layer right away.
        # In a reverse proxy scenario, this is necessary as we would otherwise hang
        # on protocols that start with a server greeting.
        self.layer.ask_now()

        self.transports = {
            self.client: StreamIO(reader, writer)
        }

    async def handle_client(self) -> None:
        # FIXME: Work around log suppression in core.
        logging.getLogger('asyncio').setLevel(logging.DEBUG)

        self.log("[sans-io] clientconnect")

        self.server_event(events.Start())
        await self.handle_connection(self.client)

        self.log("[sans-io] clientdisconnected")

        if self.transports:
            self.log("[sans-io] closing transports...")
            await asyncio.wait([
                self.close_connection(x)
                for x in self.transports
            ])
            self.log("[sans-io] transports closed!")

    async def close_connection(self, connection: Connection) -> None:
        self.log(f"closing {connection}", "debug")
        connection.state = ConnectionState.CLOSED
        io = self.transports.pop(connection)
        io.w.close()
        await io.w.wait_closed()

    async def shutdown_connection(self, connection: Connection) -> None:
        assert connection.state & ConnectionState.CAN_WRITE
        io = self.transports[connection]
        self.log(f"shutting down {connection}", "debug")

        io.w.write_eof()
        connection.state &= ~ConnectionState.CAN_WRITE

    async def handle_connection(self, connection: Connection) -> None:
        reader, writer = self.transports[connection]
        while True:
            try:
                data = await reader.read(65535)
            except socket.error:
                data = b""
            if data:
                self.server_event(events.DataReceived(connection, data))
            else:
                if connection.state is ConnectionState.CAN_READ:
                    await self.close_connection(connection)
                else:
                    connection.state &= ~ConnectionState.CAN_READ
                self.server_event(events.ConnectionClosed(connection))
                break

    async def open_connection(self, command: commands.OpenConnection) -> None:
        if not command.connection.address:
            raise ValueError("Cannot open connection, no hostname given.")
        assert command.connection not in self.transports
        try:
            reader, writer = await asyncio.open_connection(
                *command.connection.address
            )
        except IOError as e:
            self.server_event(events.OpenConnectionReply(command, str(e)))
        else:
            self.log("serverconnect")
            self.transports[command.connection] = StreamIO(reader, writer)
            command.connection.state = ConnectionState.OPEN
            self.server_event(events.OpenConnectionReply(command, None))
            await self.handle_connection(command.connection)
            self.log("serverdisconnected")

    @abc.abstractmethod
    async def handle_hook(self, hook: commands.Hook) -> None:
        pass

    def log(self, message: str, level: str = "info") -> None:
        print(message)

    def server_event(self, event: events.Event) -> None:
        try:
            self._server_event(event)
        except Exception:
            self.log(f"mitmproxy has crashed!\n{traceback.format_exc()}", level="error")

    def _server_event(self, event: events.Event) -> None:
        layer_commands = self.layer.handle_event(event)
        for command in layer_commands:
            if isinstance(command, commands.OpenConnection):
                asyncio.ensure_future(
                    self.open_connection(command)
                )
            elif isinstance(command, commands.SendData):
                try:
                    io = self.transports[command.connection]
                except KeyError:
                    raise RuntimeError(f"Cannot write to closed connection: {command.connection}")
                else:
                    io.w.write(command.data)
            elif isinstance(command, commands.CloseConnection):
                if command.connection == self.client:
                    asyncio.ensure_future(
                        self.close_connection(command.connection)
                    )
                else:
                    asyncio.ensure_future(
                        self.shutdown_connection(command.connection)
                    )
            elif isinstance(command, glue.GlueGetConnectionHandler):
                self.server_event(glue.GlueGetConnectionHandlerReply(command, self))
            elif isinstance(command, commands.Hook):
                asyncio.ensure_future(
                    self.handle_hook(command)
                )
            elif isinstance(command, commands.Log):
                self.log(command.message, command.level)
            else:
                raise RuntimeError(f"Unexpected command: {command}")


class SimpleConnectionHandler(ConnectionHandler):
    """Simple handler that does not really process any hooks."""

    hook_handlers: typing.Dict[str, typing.Callable]

    def __init__(self, reader, writer, options, hooks):
        super().__init__(reader, writer, options)
        self.hook_handlers = hooks

    async def handle_hook(
            self,
            hook: commands.Hook
    ) -> None:
        if hook.name in self.hook_handlers:
            self.hook_handlers[hook.name](hook.data)
        if hook.blocking:
            self.server_event(events.HookReply(hook))

    def log(self, message: str, level: str = "info"):
        if "Hook" not in message:
            print(message, file=sys.stderr if level in ("error", "warn") else sys.stdout)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    opts = moptions.Options()
    opts.add_option(
        "connection_strategy", str, "lazy",
        "Determine when server connections should be established.",
        choices=("eager", "lazy")
    )
    opts.mode = "regular"


    async def handle(reader, writer):
        layer_stack = [
            lambda ctx: layers.HTTPLayer(ctx, HTTPMode.regular),
            lambda ctx: setattr(ctx.server, "tls", True) or layers.ServerTLSLayer(ctx),
            lambda ctx: layers.ClientTLSLayer(ctx),
            lambda ctx: layers.HTTPLayer(ctx, HTTPMode.transparent)
        ]

        def next_layer(nl: layer.NextLayer):
            nl.layer = layer_stack.pop(0)(nl.context)
            nl.layer.debug = "  " * len(nl.context.layers)

        def request(flow: http.HTTPFlow):
            if "cached" in flow.request.path:
                flow.response = http.HTTPResponse.make(418, f"(cached) {flow.request.text}")
            if "toggle-tls" in flow.request.path:
                if flow.request.url.startswith("https://"):
                    flow.request.url = flow.request.url.replace("https://", "http://")
                else:
                    flow.request.url = flow.request.url.replace("http://", "https://")
            if "redirect" in flow.request.path:
                flow.request.url = "https://httpbin.org/robots.txt"

        await SimpleConnectionHandler(reader, writer, opts, {
            "next_layer": next_layer,
            "request": request
        }).handle_client()


    coro = asyncio.start_server(handle, '127.0.0.1', 8080, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print(f"Serving on {human.format_address(server.sockets[0].getsockname())}")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
