import asyncio
import collections
import socket
from typing import MutableMapping

from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2.context import Client, Context
from mitmproxy.proxy.protocol2.context import Connection
from mitmproxy.proxy.protocol2.reverse_proxy import ReverseProxy

StreamIO = collections.namedtuple('StreamIO', ['r', 'w'])


class ConnectionHandler:
    def __init__(self, reader, writer):
        addr = writer.get_extra_info('peername')

        self.client = Client(addr)
        self.context = Context(self.client)

        self.layer = ReverseProxy(self.context, ("example.com", 80))

        self.transports = {}  # type: MutableMapping[Connection, StreamIO]
        self.transports[self.client] = StreamIO(reader, writer)

        self.lock = asyncio.Lock()

    async def handle_client(self):
        await self.handle_connection(self.client)

        for connection in self.transports:
            await self.close(connection)

        # TODO: teardown all other conns.
        print("client connection done!")

    async def close(self, connection):
        print("Closing", connection)
        io = self.transports.pop(connection)
        try:
            await io.w.drain()
            io.w.write_eof()
        except socket.error:
            pass
        io.w.close()

    async def handle_connection(self, connection):
        connection.connected = True
        await self.server_event(events.OpenConnection(connection))
        reader, writer = self.transports[connection]
        while True:
            try:
                data = await reader.read(4096)
            except socket.error:
                data = b""
            if data:
                await self.server_event(events.ReceiveData(connection, data))
            else:
                connection.connected = False
                await self.close(connection)
                await self.server_event(events.CloseConnection(connection))
                break

    async def open_connection(self, event: events.OpenConnection):
        reader, writer = await asyncio.open_connection(
            *event.connection.address
        )
        self.transports[event.connection] = StreamIO(reader, writer)
        await self.handle_connection(event.connection)

    async def server_event(self, event: events.Event):
        print("*", event)
        async with self.lock:
            print("<#", event)
            layer_events = self.layer.handle_event(event)
            for event in layer_events:
                print("<<", event)
                if isinstance(event, events.OpenConnection):
                    asyncio.ensure_future(self.open_connection(event))
                elif isinstance(event, events.SendData):
                    self.transports[event.connection].w.write(event.data)
                else:
                    raise NotImplementedError("Unexpected event: {}".format(event))
            print("#>")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()


    async def handle(reader, writer):
        await ConnectionHandler(reader, writer).handle_client()


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
