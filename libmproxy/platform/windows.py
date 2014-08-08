import argparse
import cPickle as pickle
import os
import platform
import socket
import SocketServer
import threading
import time
from collections import OrderedDict

from pydivert.windivert import WinDivert
from pydivert.enum import Direction, Layer, Flag


PROXY_API_PORT = 8085


class Resolver(object):

    def __init__(self):
        TransparentProxy.setup()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(("127.0.0.1", PROXY_API_PORT))

        self.wfile = self.socket.makefile('wb')
        self.rfile = self.socket.makefile('rb')
        self.lock = threading.Lock()

    def original_addr(self, csock):
        client = csock.getpeername()[:2]
        with self.lock:
            pickle.dump(client, self.wfile)
            self.wfile.flush()
            return pickle.load(self.rfile)


class APIRequestHandler(SocketServer.StreamRequestHandler):
    """
    TransparentProxy API: Returns the pickled server address, port tuple
    for each received pickled client address, port tuple.
    """
    def handle(self):
        proxifier = self.server.proxifier
        while True:
            # print("API connection")
            client = pickle.load(self.rfile)
            # print("Received API Request: %s" % str(client))
            server = proxifier.client_server_map[client]
            pickle.dump(server, self.wfile)
            self.wfile.flush()
            # print("API request handled")


class APIServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


class TransparentProxy(object):
    """
    Transparent Windows Proxy for mitmproxy based on WinDivert/PyDivert.

    Requires elevated (admin) privileges. Can be started separately by manually running the file.

    This module can be used to intercept and redirect all traffic that is forwarded by the user's machine.
    This does NOT include traffic sent from the machine itself, which cannot be accomplished by this approach for
    technical reasons (we cannot distinguish between requests made by the proxy or by regular applications. Altering the
    destination the proxy is seeing to some meta address does not work with TLS as the address doesn't match the
    signature.)

    How it works:

    (1) First, we intercept all packages that are forwarded by the OS (WinDivert's NETWORK_FORWARD layer) and whose
    destination port matches our filter (80 and 443 by default).
    For each intercepted package, we
        1. Store the source -> destination mapping (address and port)
        2. Remove the package from the network (by not reinjecting it).
        3. Re-inject the package into the local network stack, but with the destination address changed to the proxy.

    (2) Next, the proxy receives the forwarded packet, but does not know the real destination yet (which we overwrote
    with the proxy's address). On Linux, we would now call getsockopt(SO_ORIGINAL_DST), but that unfortunately doesn't
    work on Windows. However, we still have the correct source information. As a workaround, we now access the forward
    module's API (see APIRequestHandler), submit the source information and get the actual destination back (which the
    forward module stored in (1.3)).

    (3) The proxy now establish the upstream connection as usual.

    (4) Finally, the proxy sends the response back to the client. To make it work, we need to change the packet's source
    address back to the original destination (using the mapping from (1.3)), to which the client believes he is talking
    to.
    """

    def __init__(self,
                 redirect_ports=(80, 443),
                 proxy_addr=False, proxy_port=8080,
                 api_host="localhost", api_port=PROXY_API_PORT,
                 cache_size=65536):
        """
        :param redirect_ports: if the destination port is in this tuple, the requests are redirected to the proxy.
        :param proxy_addr: IP address of the proxy (IP within a network, 127.0.0.1 does not work). By default,
        this is detected automatically.
        :param proxy_port: Port the proxy is listenting on.
        :param api_host: Host the forward module API is listening on.
        :param api_port: Port the forward module API is listening on.
        :param cache_size: Maximum number of connection tuples that are stored. Only relevant in very high
        load scenarios.
        """

        if not proxy_addr:
            # Auto-Detect local IP.
            # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            proxy_addr = s.getsockname()[0]
            s.close()

        self.client_server_map = OrderedDict()
        self.proxy_addr, self.proxy_port = proxy_addr, proxy_port
        self.connection_cache_size = cache_size

        self.api_server = APIServer((api_host, api_port), APIRequestHandler)
        self.api_server.proxifier = self
        self.api_server_thread = threading.Thread(target=self.api_server.serve_forever)
        self.api_server_thread.daemon = True

        arch = "amd64" if platform.architecture()[0] == "64bit" else "x86"
        self.driver = WinDivert(os.path.join(os.path.dirname(__file__), "..", "contrib",
                                             "windivert", arch, "WinDivert.dll"))
        self.driver.register()

        filter_forward = " or ".join(
            ("tcp.DstPort == %d" % p) for p in redirect_ports)
        self.handle_forward = self.driver.open_handle(filter=filter_forward, layer=Layer.NETWORK_FORWARD)
        self.forward_thread = threading.Thread(target=self.redirect)
        self.forward_thread.daemon = True

        filter_local = "outbound and tcp.SrcPort == %d" % proxy_port
        self.handle_local = self.driver.open_handle(filter=filter_local, layer=Layer.NETWORK)
        self.local_thread = threading.Thread(target=self.adjust_source)
        self.local_thread.daemon = True

        self.handle_icmp = self.driver.open_handle(filter="icmp", layer=Layer.NETWORK, flags=Flag.DROP)

    @classmethod
    def setup(cls):
        # TODO: Make sure that server can be killed cleanly. That's a bit difficult as we don't have access to
        # controller.should_exit when this is called.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_unavailable = s.connect_ex(("127.0.0.1", PROXY_API_PORT))
        if server_unavailable:
            proxifier = TransparentProxy()
            proxifier.start()

    def start(self):
        self.api_server_thread.start()
        self.local_thread.start()
        self.forward_thread.start()

    def shutdown(self):
        self.handle_forward.close()
        self.handle_local.close()
        self.handle_icmp.close()
        self.api_server.shutdown()

    def recv(self, handle):
        """
        Convenience function that receives a packet from the passed handler and handles error codes.
        If the process has been shut down, (None, None) is returned.
        """
        try:
            raw_packet, metadata = handle.recv()
            return self.driver.parse_packet(raw_packet), metadata
        except WindowsError, e:
            if e.winerror == 995:
                return None, None
            else:
                raise e

    def redirect(self):
        """
        Redirect packages to the proxy
        """
        while True:
            packet, metadata = self.recv(self.handle_forward)
            if not packet:
                return

            # print(" * Redirect client -> server to proxy")
            # print("%s:%s -> %s:%s" % (packet.src_addr, packet.src_port, packet.dst_addr, packet.dst_port))
            client = (packet.src_addr, packet.src_port)
            server = (packet.dst_addr, packet.dst_port)

            if client in self.client_server_map:
                del self.client_server_map[client]
            while len(self.client_server_map) > self.connection_cache_size:
                self.client_server_map.popitem(False)

            self.client_server_map[client] = server

            packet.dst_addr, packet.dst_port = self.proxy_addr, self.proxy_port
            metadata.direction = Direction.INBOUND

            packet = self.driver.update_packet_checksums(packet)
            self.handle_local.send((packet.raw, metadata))

    def adjust_source(self):
        """
        Spoof source address of packets send from the proxy to the client
        """
        while True:
            packet, metadata = self.recv(self.handle_local)
            if not packet:
                return

            # If the proxy responds to the client, let the client believe the target server sent the packets.
            # print(" * Adjust proxy -> client")
            client = (packet.dst_addr, packet.dst_port)
            server = self.client_server_map[client]
            packet.src_addr, packet.src_port = server

            packet = self.driver.update_packet_checksums(packet)
            self.handle_local.send((packet.raw, metadata))

    def icmp_block(self):
        """
        Block all ICMP requests (which are sent on Windows by default).
        In layman's terms: If we don't do this, our proxy machine tells the client that it can directly connect to the
        real gateway if they are on the same network.
        """
        while True:
            packet, metadata = self.recv(self.handle_icmp)
            if not packet:
                return
                # no nothing with the received packet, do not reinject it.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Windows Transparent Proxy")
    parser.add_argument("--redirect-ports", nargs="+", type=int, default=[80, 443], metavar="80",
                        help="ports that should be forwarded to the proxy")
    parser.add_argument("--proxy-addr", default=False,
                        help="proxy server address")
    parser.add_argument("--proxy-port", type=int, default=8080,
                        help="proxy server port")
    parser.add_argument("--api-host", default="localhost",
                        help="API hostname to bind to")
    parser.add_argument("--api-port", type=int, default=PROXY_API_PORT,
                        help="API port")
    parser.add_argument("--cache-size", type=int, default=65536,
                        help="maximum connection cache size")
    options = parser.parse_args()
    proxifier = TransparentProxy(**vars(options))
    proxifier.start()
    print(" * Transparent proxy active.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" * Shutting down...")
        proxifier.shutdown()
        print(" * Shut down.")