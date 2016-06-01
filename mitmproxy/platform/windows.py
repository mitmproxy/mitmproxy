import collections
import ctypes
import ctypes.wintypes
import os
import socket
import struct
import threading
import time

import configargparse
from pydivert import enum
from pydivert import windivert
from six.moves import cPickle as pickle
from six.moves import socketserver

PROXY_API_PORT = 8085


class Resolver(object):

    def __init__(self):
        TransparentProxy.setup()
        self.socket = None
        self.lock = threading.RLock()
        self._connect()

    def _connect(self):
        if self.socket:
            self.socket.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(("127.0.0.1", PROXY_API_PORT))

        self.wfile = self.socket.makefile('wb')
        self.rfile = self.socket.makefile('rb')
        pickle.dump(os.getpid(), self.wfile)

    def original_addr(self, csock):
        client = csock.getpeername()[:2]
        with self.lock:
            try:
                pickle.dump(client, self.wfile)
                self.wfile.flush()
                addr = pickle.load(self.rfile)
                if addr is None:
                    raise RuntimeError("Cannot resolve original destination.")
                addr = list(addr)
                addr[0] = str(addr[0])
                addr = tuple(addr)
                return addr
            except (EOFError, socket.error):
                self._connect()
                return self.original_addr(csock)


class APIRequestHandler(socketserver.StreamRequestHandler):

    """
    TransparentProxy API: Returns the pickled server address, port tuple
    for each received pickled client address, port tuple.
    """

    def handle(self):
        proxifier = self.server.proxifier
        pid = None
        try:
            pid = pickle.load(self.rfile)
            if pid is not None:
                proxifier.trusted_pids.add(pid)

            while True:
                client = pickle.load(self.rfile)
                server = proxifier.client_server_map.get(client, None)
                pickle.dump(server, self.wfile)
                self.wfile.flush()

        except (EOFError, socket.error):
            proxifier.trusted_pids.discard(pid)


class APIServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, proxifier, *args, **kwargs):
        socketserver.TCPServer.__init__(self, *args, **kwargs)
        self.proxifier = proxifier
        self.daemon_threads = True


# Windows error.h
ERROR_INSUFFICIENT_BUFFER = 0x7A


# http://msdn.microsoft.com/en-us/library/windows/desktop/bb485761(v=vs.85).aspx
class MIB_TCPROW2(ctypes.Structure):
    _fields_ = [
        ('dwState', ctypes.wintypes.DWORD),
        ('dwLocalAddr', ctypes.wintypes.DWORD),
        ('dwLocalPort', ctypes.wintypes.DWORD),
        ('dwRemoteAddr', ctypes.wintypes.DWORD),
        ('dwRemotePort', ctypes.wintypes.DWORD),
        ('dwOwningPid', ctypes.wintypes.DWORD),
        ('dwOffloadState', ctypes.wintypes.DWORD)
    ]


# http://msdn.microsoft.com/en-us/library/windows/desktop/bb485772(v=vs.85).aspx
def MIB_TCPTABLE2(size):
    class _MIB_TCPTABLE2(ctypes.Structure):
        _fields_ = [('dwNumEntries', ctypes.wintypes.DWORD),
                    ('table', MIB_TCPROW2 * size)]

    return _MIB_TCPTABLE2()


class TransparentProxy(object):

    """
    Transparent Windows Proxy for mitmproxy based on WinDivert/PyDivert.

    Requires elevated (admin) privileges. Can be started separately by manually running the file.

    This module can be used to intercept and redirect all traffic that is forwarded by the user's machine and
    traffic sent from the machine itself.

    How it works:

    (1) First, we intercept all packages that match our filter (destination port 80 and 443 by default).
    We both consider traffic that is forwarded by the OS (WinDivert's NETWORK_FORWARD layer) as well as traffic
    sent from the local machine (WinDivert's NETWORK layer). In the case of traffic from the local machine, we need to
    distinguish between traffc sent from applications and traffic sent from the proxy. To accomplish this, we use
    Windows' GetTcpTable2 syscall to determine the source application's PID.

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

    Limitations:

    - No IPv6 support. (Pull Requests welcome)
    - TCP ports do not get re-used simulateously on the client, i.e. the proxy will fail if application X
      connects to example.com and example.org from 192.168.0.42:4242 simultaneously. This could be mitigated by
      introducing unique "meta-addresses" which mitmproxy sees, but this would remove the correct client info from
      mitmproxy.

    """

    def __init__(self,
                 mode="both",
                 redirect_ports=(80, 443), custom_filter=None,
                 proxy_addr=False, proxy_port=8080,
                 api_host="localhost", api_port=PROXY_API_PORT,
                 cache_size=65536):
        """
        :param mode: Redirection operation mode: "forward" to only redirect forwarded packets, "local" to only redirect
        packets originating from the local machine, "both" to redirect both.
        :param redirect_ports: if the destination port is in this tuple, the requests are redirected to the proxy.
        :param custom_filter: specify a custom WinDivert filter to select packets that should be intercepted. Overrides
        redirect_ports setting.
        :param proxy_addr: IP address of the proxy (IP within a network, 127.0.0.1 does not work). By default,
        this is detected automatically.
        :param proxy_port: Port the proxy is listenting on.
        :param api_host: Host the forward module API is listening on.
        :param api_port: Port the forward module API is listening on.
        :param cache_size: Maximum number of connection tuples that are stored. Only relevant in very high
        load scenarios.
        """
        if proxy_port in redirect_ports:
            raise ValueError("The proxy port must not be a redirect port.")

        if not proxy_addr:
            # Auto-Detect local IP.
            # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            proxy_addr = s.getsockname()[0]
            s.close()

        self.mode = mode
        self.proxy_addr, self.proxy_port = proxy_addr, proxy_port
        self.connection_cache_size = cache_size

        self.client_server_map = collections.OrderedDict()

        self.api = APIServer(self, (api_host, api_port), APIRequestHandler)
        self.api_thread = threading.Thread(target=self.api.serve_forever)
        self.api_thread.daemon = True

        self.driver = windivert.WinDivert()
        self.driver.register()

        self.request_filter = custom_filter or " or ".join(
            ("tcp.DstPort == %d" %
             p) for p in redirect_ports)
        self.request_forward_handle = None
        self.request_forward_thread = threading.Thread(
            target=self.request_forward)
        self.request_forward_thread.daemon = True

        self.addr_pid_map = dict()
        self.trusted_pids = set()
        self.tcptable2 = MIB_TCPTABLE2(0)
        self.tcptable2_size = ctypes.wintypes.DWORD(0)
        self.request_local_handle = None
        self.request_local_thread = threading.Thread(target=self.request_local)
        self.request_local_thread.daemon = True

        # The proxy server responds to the client. To the client,
        # this response should look like it has been sent by the real target
        self.response_filter = "outbound and tcp.SrcPort == %d" % proxy_port
        self.response_handle = None
        self.response_thread = threading.Thread(target=self.response)
        self.response_thread.daemon = True

        self.icmp_handle = None

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
        self.api_thread.start()

        # Block all ICMP requests (which are sent on Windows by default).
        # In layman's terms: If we don't do this, our proxy machine tells the client that it can directly connect to the
        # real gateway if they are on the same network.
        self.icmp_handle = self.driver.open_handle(
            filter="icmp",
            layer=enum.Layer.NETWORK,
            flags=enum.Flag.DROP)

        self.response_handle = self.driver.open_handle(
            filter=self.response_filter,
            layer=enum.Layer.NETWORK)
        self.response_thread.start()

        if self.mode == "forward" or self.mode == "both":
            self.request_forward_handle = self.driver.open_handle(
                filter=self.request_filter,
                layer=enum.Layer.NETWORK_FORWARD)
            self.request_forward_thread.start()
        if self.mode == "local" or self.mode == "both":
            self.request_local_handle = self.driver.open_handle(
                filter=self.request_filter,
                layer=enum.Layer.NETWORK)
            self.request_local_thread.start()

    def shutdown(self):
        if self.mode == "local" or self.mode == "both":
            self.request_local_handle.close()
        if self.mode == "forward" or self.mode == "both":
            self.request_forward_handle.close()

        self.response_handle.close()
        self.icmp_handle.close()
        self.api.shutdown()

    def recv(self, handle):
        """
        Convenience function that receives a packet from the passed handler and handles error codes.
        If the process has been shut down, (None, None) is returned.
        """
        try:
            raw_packet, metadata = handle.recv()
            return self.driver.parse_packet(raw_packet), metadata
        except WindowsError as e:
            if e.winerror == 995:
                return None, None
            else:
                raise

    def fetch_pids(self):
        ret = ctypes.windll.iphlpapi.GetTcpTable2(
            ctypes.byref(
                self.tcptable2), ctypes.byref(
                self.tcptable2_size), 0)
        if ret == ERROR_INSUFFICIENT_BUFFER:
            self.tcptable2 = MIB_TCPTABLE2(self.tcptable2_size.value)
            self.fetch_pids()
        elif ret == 0:
            for row in self.tcptable2.table[:self.tcptable2.dwNumEntries]:
                local = (
                    socket.inet_ntoa(struct.pack('L', row.dwLocalAddr)),
                    socket.htons(row.dwLocalPort)
                )
                self.addr_pid_map[local] = row.dwOwningPid
        else:
            raise RuntimeError("Unknown GetTcpTable2 return code: %s" % ret)

    def request_local(self):
        while True:
            packet, metadata = self.recv(self.request_local_handle)
            if not packet:
                return

            client = (packet.src_addr, packet.src_port)

            if client not in self.addr_pid_map:
                self.fetch_pids()

            # If this fails, we most likely have a connection from an external client to
            # a local server on 80/443. In this, case we always want to proxy
            # the request.
            pid = self.addr_pid_map.get(client, None)

            if pid not in self.trusted_pids:
                self._request(packet, metadata)
            else:
                self.request_local_handle.send((packet.raw, metadata))

    def request_forward(self):
        """
        Redirect packages to the proxy
        """
        while True:
            packet, metadata = self.recv(self.request_forward_handle)
            if not packet:
                return

            self._request(packet, metadata)

    def _request(self, packet, metadata):
        # print(" * Redirect client -> server to proxy")
        # print("%s:%s -> %s:%s" % (packet.src_addr, packet.src_port, packet.dst_addr, packet.dst_port))
        client = (packet.src_addr, packet.src_port)
        server = (packet.dst_addr, packet.dst_port)

        if client in self.client_server_map:
            # Force re-add to mark as "newest" entry in the dict.
            del self.client_server_map[client]
        while len(self.client_server_map) > self.connection_cache_size:
            self.client_server_map.popitem(False)

        self.client_server_map[client] = server

        packet.dst_addr, packet.dst_port = self.proxy_addr, self.proxy_port
        metadata.direction = enum.Direction.INBOUND

        packet = self.driver.update_packet_checksums(packet)
        # Use any handle thats on the NETWORK layer - request_local may be
        # unavailable.
        self.response_handle.send((packet.raw, metadata))

    def response(self):
        """
        Spoof source address of packets send from the proxy to the client
        """
        while True:
            packet, metadata = self.recv(self.response_handle)
            if not packet:
                return

            # If the proxy responds to the client, let the client believe the target server sent the packets.
            # print(" * Adjust proxy -> client")
            client = (packet.dst_addr, packet.dst_port)
            server = self.client_server_map.get(client, None)
            if server:
                packet.src_addr, packet.src_port = server
            else:
                print("Warning: Previously unseen connection from proxy to %s:%s." % client)

            packet = self.driver.update_packet_checksums(packet)
            self.response_handle.send((packet.raw, metadata))


if __name__ == "__main__":
    parser = configargparse.ArgumentParser(
        description="Windows Transparent Proxy")
    parser.add_argument(
        '--mode',
        choices=[
            'forward',
            'local',
            'both'],
        default="both",
        help='redirection operation mode: "forward" to only redirect forwarded packets, '
        '"local" to only redirect packets originating from the local machine')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--redirect-ports",
        nargs="+",
        type=int,
        default=[
            80,
            443],
        metavar="80",
        help="ports that should be forwarded to the proxy")
    group.add_argument(
        "--custom-filter",
        default=None,
        metavar="WINDIVERT_FILTER",
        help="Custom WinDivert interception rule.")
    parser.add_argument("--proxy-addr", default=False,
                        help="Proxy Server Address")
    parser.add_argument("--proxy-port", type=int, default=8080,
                        help="Proxy Server Port")
    parser.add_argument("--api-host", default="localhost",
                        help="API hostname to bind to")
    parser.add_argument("--api-port", type=int, default=PROXY_API_PORT,
                        help="API port")
    parser.add_argument("--cache-size", type=int, default=65536,
                        help="Maximum connection cache size")
    options = parser.parse_args()
    proxy = TransparentProxy(**vars(options))
    proxy.start()
    print(" * Transparent proxy active.")
    print("   Filter: {0}".format(proxy.request_filter))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" * Shutting down...")
        proxy.shutdown()
        print(" * Shut down.")
