# This is outdated, only the async version is kept up to date.
"""
Minimal server implementation based on https://docs.python.org/3/library/selectors.html#examples.
May be worth to replace this with something asyncio-based to overcome the issues outlined by the
FIXMEs below.
"""
import functools
import selectors
import socket
from typing import MutableMapping

from mitmproxy.proxy.protocol2 import events, commands
from mitmproxy.proxy.protocol2.context import Connection
from mitmproxy.proxy.protocol2.context import Context, Client
from mitmproxy.proxy.protocol2.events import Event
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.reverse_proxy import ReverseProxy


class ConnectionHandler:
    def __init__(self, sel: selectors.BaseSelector, sock: socket.socket, addr: tuple) -> None:
        self.connections = {}  # type: MutableMapping[Connection, socket.socket]
        self.sel = sel
        self.sock = sock
        self.addr = addr

        sock.setblocking(False)

        client = Client(addr)
        context = Context(client)

        layer = ReverseProxy(context, ("example.com", 80))

        # self.server_event(layer, commands.OpenConnection(client))

        callback = functools.partial(self.read, layer, client)

        self.sel.register(
            sock,
            selectors.EVENT_READ,
            callback
        )

        self.connections[client] = sock

    def read(self, layer: Layer, conn: Connection, sock: socket.socket, mask: int):
        data = sock.recv(4096)
        if data:
            self.server_event(layer, events.DataReceived(conn, data))
        else:
            # TODO: Needs proper teardown.
            self.sel.unregister(sock)
            sock.close()
            self.server_event(layer, events.ConnectionClosed(conn))

    def server_event(self, layer: Layer, event: Event):
        print(">>", event)
        layer_events = layer.handle_event(event)
        for event in layer_events:
            print("<<", event)
            if isinstance(event, commands.OpenConnection):
                # FIXME: This is blocking!
                sock = socket.create_connection(event.connection.address)
                sock.setblocking(False)
                event.connection.connected = True
                layer_events.send(42)
                callback = functools.partial(self.read, layer, event.connection)
                self.sel.register(
                    sock,
                    selectors.EVENT_READ,
                    callback
                )
                self.connections[event.connection] = sock
            elif isinstance(event, commands.SendData):
                # FIXME: This may fail.
                self.connections[event.connection].sendall(event.data)
            else:
                raise NotImplementedError("Unexpected event: {}".format(event))


class TCPServer:
    def __init__(self, address):
        self.connections = set()
        self.server_sock = socket.socket()
        self.server_sock.bind(address)
        self.server_sock.listen(100)
        self.server_sock.setblocking(False)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.server_sock, selectors.EVENT_READ, self.accept)

    def accept(self, server_sock, mask):
        sock, addr = server_sock.accept()  # Should be ready
        connection = ConnectionHandler(self.sel, sock, addr)
        self.connections.add(connection)

    def run(self):
        while True:
            self.tick(None)

    def tick(self, timeout):
        for key, mask in self.sel.select(timeout):
            callback = key.data
            callback(key.fileobj, mask)


if __name__ == '__main__':
    s = TCPServer(('', 8080))
    s.run()
