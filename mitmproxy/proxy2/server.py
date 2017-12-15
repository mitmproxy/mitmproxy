"""
Proxy Server Implementation using asyncio.
The very high level overview is as follows:

    - Spawn one coroutine per client connection and create a reverse proxy layer to example.com
    - Process any commands from layer (such as opening a server connection)
    - Wait for any IO and send it as events to top layer.
"""
import abc
import asyncio
import socket
import typing

from mitmproxy import options as moptions
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import events, commands, layers, layer
from mitmproxy.proxy2.context import Client, Context, Connection


class StreamIO(typing.NamedTuple):
    r: asyncio.StreamReader
    w: asyncio.StreamWriter


class ConnectionHandler(metaclass=abc.ABCMeta):
    transports: typing.MutableMapping[Connection, StreamIO]

    def __init__(self, reader, writer, options):
        addr = writer.get_extra_info('peername')

        self.client = Client(addr)
        self.context = Context(self.client, options)

        if options.mode == "regular":
            self.layer = layers.modes.HttpProxy(self.context)
        elif options.mode.startswith("reverse:"):
            self.layer = layers.modes.ReverseProxy(self.context)
        else:
            raise NotImplementedError("Mode not implemented.")

        self.transports = {
            self.client: StreamIO(reader, writer)
        }

    async def handle_client(self):
        self.log("clientconnect")

        self.server_event(events.Start())
        await self.handle_connection(self.client)

        self.log("clientdisconnect")

        if self.transports:
            await asyncio.wait([
                self.close_connection(x)
                for x in self.transports
            ])

        # self._debug("transports closed!")

    async def close_connection(self, connection):
        try:
            io = self.transports.pop(connection)
        except KeyError:
            self.log(f"already closed: {connection}", "warn")
            return
        else:
            self.log(f"closing {connection}", "debug")
        try:
            await io.w.drain()
            io.w.write_eof()
        except socket.error:
            pass
        io.w.close()

    async def handle_connection(self, connection):
        reader, writer = self.transports[connection]
        while True:
            try:
                data = await reader.read(65535)
            except socket.error:
                data = b""
            if data:
                self.server_event(events.DataReceived(connection, data))
            else:
                connection.connected = False
                if connection in self.transports:
                    await self.close_connection(connection)
                self.server_event(events.ConnectionClosed(connection))
                break

    async def open_connection(self, command: commands.OpenConnection):
        if not command.connection.address:
            raise ValueError("Cannot open connection, no hostname given.")
        try:
            reader, writer = await asyncio.open_connection(
                *command.connection.address
            )
        except IOError as e:
            self.server_event(events.OpenConnectionReply(command, str(e)))
        else:
            self.log("serverconnect")
            self.transports[command.connection] = StreamIO(reader, writer)
            command.connection.connected = True
            self.server_event(events.OpenConnectionReply(command, None))
            await self.handle_connection(command.connection)
            self.log("serverdisconnect")

    @abc.abstractmethod
    async def handle_hook(self, hook: commands.Hook) -> None:
        pass

    def log(self, message: str, level: str = "info") -> None:
        print(message)

    def server_event(self, event: events.Event) -> None:
        layer_commands = self.layer.handle_event(event)
        for command in layer_commands:
            if isinstance(command, commands.OpenConnection):
                asyncio.ensure_future(
                    self.open_connection(command)
                )
            elif isinstance(command, commands.SendData):
                self.transports[command.connection].w.write(command.data)
            elif isinstance(command, commands.CloseConnection):
                asyncio.ensure_future(
                    self.close_connection(command.connection)
                )
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

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    opts = moptions.Options()
    opts.mode = "reverse:example.com"
    # test client-tls-first scenario
    # opts.upstream_cert = False

    layers.ClientTLSLayer.debug = ""
    layers.ServerTLSLayer.debug = "  "
    layers.TCPLayer.debug = "    "

    async def handle(reader, writer):
        layer_stack = [
            layers.ClientTLSLayer,
            #layers.ServerTLSLayer,
            layers.TCPLayer,
            # lambda c: layers.HTTPLayer(c, HTTPMode.transparent),
        ]

        def next_layer(nl: layer.NextLayer):
            nl.layer = layer_stack.pop(0)(nl.context)

        await SimpleConnectionHandler(reader, writer, opts, {
            "next_layer": next_layer
        }).handle_client()

    coro = asyncio.start_server(handle, '127.0.0.1', 8080, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
