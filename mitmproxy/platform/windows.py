import contextlib
import ctypes
import ctypes.wintypes
import io
import json
import os
import re
import socket
import socketserver
import threading
import time
import typing

import click
import collections
import collections.abc
import pydivert
import pydivert.consts

if typing.TYPE_CHECKING:
    class WindowsError(OSError):
        @property
        def winerror(self) -> int:
            return 42

REDIRECT_API_HOST = "127.0.0.1"
REDIRECT_API_PORT = 8085


##########################
# Resolver

def read(rfile: io.BufferedReader) -> typing.Any:
    x = rfile.readline().strip()
    return json.loads(x)


def write(data, wfile: io.BufferedWriter) -> None:
    wfile.write(json.dumps(data).encode() + b"\n")
    wfile.flush()


class Resolver:
    sock: socket.socket
    lock: threading.RLock

    def __init__(self):
        self.sock = None
        self.lock = threading.RLock()

    def setup(self):
        with self.lock:
            TransparentProxy.setup()
            self._connect()

    def _connect(self):
        if self.sock:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((REDIRECT_API_HOST, REDIRECT_API_PORT))

        self.wfile = self.sock.makefile('wb')
        self.rfile = self.sock.makefile('rb')
        write(os.getpid(), self.wfile)

    def original_addr(self, csock: socket.socket):
        ip, port = csock.getpeername()[:2]
        ip = re.sub(r"^::ffff:(?=\d+.\d+.\d+.\d+$)", "", ip)
        ip = ip.split("%", 1)[0]
        with self.lock:
            try:
                write((ip, port), self.wfile)
                addr = read(self.rfile)
                if addr is None:
                    raise RuntimeError("Cannot resolve original destination.")
                return tuple(addr)
            except (EOFError, OSError):
                self._connect()
                return self.original_addr(csock)


class APIRequestHandler(socketserver.StreamRequestHandler):
    """
    TransparentProxy API: Returns the pickled server address, port tuple
    for each received pickled client address, port tuple.
    """

    def handle(self):
        proxifier: TransparentProxy = self.server.proxifier
        try:
            pid: int = read(self.rfile)
            with proxifier.exempt(pid):
                while True:
                    client = tuple(read(self.rfile))
                    try:
                        server = proxifier.client_server_map[client]
                    except KeyError:
                        server = None
                    write(server, self.wfile)
        except (EOFError, OSError):
            pass


class APIServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, proxifier, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxifier = proxifier
        self.daemon_threads = True


##########################
# Windows API

# from Windows' error.h
ERROR_INSUFFICIENT_BUFFER = 0x7A

IN6_ADDR = ctypes.c_ubyte * 16
IN4_ADDR = ctypes.c_ubyte * 4


#
# IPv6
#

# https://msdn.microsoft.com/en-us/library/windows/desktop/aa366896(v=vs.85).aspx
class MIB_TCP6ROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ('ucLocalAddr', IN6_ADDR),
        ('dwLocalScopeId', ctypes.wintypes.DWORD),
        ('dwLocalPort', ctypes.wintypes.DWORD),
        ('ucRemoteAddr', IN6_ADDR),
        ('dwRemoteScopeId', ctypes.wintypes.DWORD),
        ('dwRemotePort', ctypes.wintypes.DWORD),
        ('dwState', ctypes.wintypes.DWORD),
        ('dwOwningPid', ctypes.wintypes.DWORD),
    ]


# https://msdn.microsoft.com/en-us/library/windows/desktop/aa366905(v=vs.85).aspx
def MIB_TCP6TABLE_OWNER_PID(size):
    class _MIB_TCP6TABLE_OWNER_PID(ctypes.Structure):
        _fields_ = [
            ('dwNumEntries', ctypes.wintypes.DWORD),
            ('table', MIB_TCP6ROW_OWNER_PID * size)
        ]

    return _MIB_TCP6TABLE_OWNER_PID()


#
# IPv4
#

# https://msdn.microsoft.com/en-us/library/windows/desktop/aa366913(v=vs.85).aspx
class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ('dwState', ctypes.wintypes.DWORD),
        ('ucLocalAddr', IN4_ADDR),
        ('dwLocalPort', ctypes.wintypes.DWORD),
        ('ucRemoteAddr', IN4_ADDR),
        ('dwRemotePort', ctypes.wintypes.DWORD),
        ('dwOwningPid', ctypes.wintypes.DWORD),
    ]


# https://msdn.microsoft.com/en-us/library/windows/desktop/aa366921(v=vs.85).aspx
def MIB_TCPTABLE_OWNER_PID(size):
    class _MIB_TCPTABLE_OWNER_PID(ctypes.Structure):
        _fields_ = [
            ('dwNumEntries', ctypes.wintypes.DWORD),
            ('table', MIB_TCPROW_OWNER_PID * size)
        ]

    return _MIB_TCPTABLE_OWNER_PID()


TCP_TABLE_OWNER_PID_CONNECTIONS = 4


class TcpConnectionTable(collections.abc.Mapping):
    DEFAULT_TABLE_SIZE = 4096

    def __init__(self):
        self._tcp = MIB_TCPTABLE_OWNER_PID(self.DEFAULT_TABLE_SIZE)
        self._tcp_size = ctypes.wintypes.DWORD(self.DEFAULT_TABLE_SIZE)
        self._tcp6 = MIB_TCP6TABLE_OWNER_PID(self.DEFAULT_TABLE_SIZE)
        self._tcp6_size = ctypes.wintypes.DWORD(self.DEFAULT_TABLE_SIZE)
        self._map = {}

    def __getitem__(self, item):
        return self._map[item]

    def __iter__(self):
        return self._map.__iter__()

    def __len__(self):
        return self._map.__len__()

    def refresh(self):
        self._map = {}
        self._refresh_ipv4()
        self._refresh_ipv6()

    def _refresh_ipv4(self):
        ret = ctypes.windll.iphlpapi.GetExtendedTcpTable(
            ctypes.byref(self._tcp),
            ctypes.byref(self._tcp_size),
            False,
            socket.AF_INET,
            TCP_TABLE_OWNER_PID_CONNECTIONS,
            0
        )
        if ret == 0:
            for row in self._tcp.table[:self._tcp.dwNumEntries]:
                local_ip = socket.inet_ntop(socket.AF_INET, bytes(row.ucLocalAddr))
                local_port = socket.htons(row.dwLocalPort)
                self._map[(local_ip, local_port)] = row.dwOwningPid
        elif ret == ERROR_INSUFFICIENT_BUFFER:
            self._tcp = MIB_TCPTABLE_OWNER_PID(self._tcp_size.value)
            # no need to update size, that's already done.
            self._refresh_ipv4()
        else:
            raise RuntimeError("[IPv4] Unknown GetExtendedTcpTable return code: %s" % ret)

    def _refresh_ipv6(self):
        ret = ctypes.windll.iphlpapi.GetExtendedTcpTable(
            ctypes.byref(self._tcp6),
            ctypes.byref(self._tcp6_size),
            False,
            socket.AF_INET6,
            TCP_TABLE_OWNER_PID_CONNECTIONS,
            0
        )
        if ret == 0:
            for row in self._tcp6.table[:self._tcp6.dwNumEntries]:
                local_ip = socket.inet_ntop(socket.AF_INET6, bytes(row.ucLocalAddr))
                local_port = socket.htons(row.dwLocalPort)
                self._map[(local_ip, local_port)] = row.dwOwningPid
        elif ret == ERROR_INSUFFICIENT_BUFFER:
            self._tcp6 = MIB_TCP6TABLE_OWNER_PID(self._tcp6_size.value)
            # no need to update size, that's already done.
            self._refresh_ipv6()
        else:
            raise RuntimeError("[IPv6] Unknown GetExtendedTcpTable return code: %s" % ret)


def get_local_ip() -> typing.Optional[str]:
    # Auto-Detect local IP. This is required as re-injecting to 127.0.0.1 does not work.
    # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def get_local_ip6(reachable: str) -> typing.Optional[str]:
    # The same goes for IPv6, with the added difficulty that .connect() fails if
    # the target network is not reachable.
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    try:
        s.connect((reachable, 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


class Redirect(threading.Thread):
    daemon = True
    windivert: pydivert.WinDivert

    def __init__(
        self,
        handle: typing.Callable[[pydivert.Packet], None],
        filter: str,
        layer: pydivert.Layer = pydivert.Layer.NETWORK,
        flags: pydivert.Flag = 0
    ) -> None:
        self.handle = handle
        self.windivert = pydivert.WinDivert(filter, layer, flags=flags)
        super().__init__()

    def start(self):
        self.windivert.open()
        super().start()

    def run(self):
        while True:
            try:
                packet = self.windivert.recv()
            except WindowsError as e:
                if e.winerror == 995:
                    return
                else:
                    raise
            else:
                self.handle(packet)

    def shutdown(self):
        self.windivert.close()

    def recv(self) -> typing.Optional[pydivert.Packet]:
        """
        Convenience function that receives a packet from the passed handler and handles error codes.
        If the process has been shut down, None is returned.
        """
        try:
            return self.windivert.recv()
        except WindowsError as e:
            if e.winerror == 995:
                return None
            else:
                raise


class RedirectLocal(Redirect):
    trusted_pids: typing.Set[int]

    def __init__(
        self,
        redirect_request: typing.Callable[[pydivert.Packet], None],
        filter: str
    ) -> None:
        self.tcp_connections = TcpConnectionTable()
        self.trusted_pids = set()
        self.redirect_request = redirect_request
        super().__init__(self.handle, filter)

    def handle(self, packet):
        client = (packet.src_addr, packet.src_port)

        if client not in self.tcp_connections:
            self.tcp_connections.refresh()

        # If this fails, we most likely have a connection from an external client.
        # In this, case we always want to proxy the request.
        pid = self.tcp_connections.get(client, None)

        if pid not in self.trusted_pids:
            self.redirect_request(packet)
        else:
            # It's not really clear why we need to recalculate the checksum here,
            # but this was identified as necessary in https://github.com/mitmproxy/mitmproxy/pull/3174.
            self.windivert.send(packet, recalculate_checksum=True)


TConnection = typing.Tuple[str, int]


class ClientServerMap:
    """A thread-safe LRU dict."""
    connection_cache_size: typing.ClassVar[int] = 65536

    def __init__(self):
        self._lock = threading.Lock()
        self._map = collections.OrderedDict()

    def __getitem__(self, item: TConnection) -> TConnection:
        with self._lock:
            return self._map[item]

    def __setitem__(self, key: TConnection, value: TConnection) -> None:
        with self._lock:
            self._map[key] = value
            self._map.move_to_end(key)
            while len(self._map) > self.connection_cache_size:
                self._map.popitem(False)


class TransparentProxy:
    """
    Transparent Windows Proxy for mitmproxy based on WinDivert/PyDivert. This module can be used to
    redirect both traffic that is forwarded by the host and traffic originating from the host itself.

    Requires elevated (admin) privileges. Can be started separately by manually running the file.

    How it works:

    (1) First, we intercept all packages that match our filter.
    We both consider traffic that is forwarded by the OS (WinDivert's NETWORK_FORWARD layer) as well
    as traffic sent from the local machine (WinDivert's NETWORK layer). In the case of traffic from
    the local machine, we need to exempt packets sent from the proxy to not create a redirect loop.
    To accomplish this, we use Windows' GetExtendedTcpTable syscall and determine the source
    application's PID.

    For each intercepted package, we
        1. Store the source -> destination mapping (address and port)
        2. Remove the package from the network (by not reinjecting it).
        3. Re-inject the package into the local network stack, but with the destination address
           changed to the proxy.

    (2) Next, the proxy receives the forwarded packet, but does not know the real destination yet
    (which we overwrote with the proxy's address). On Linux, we would now call
    getsockopt(SO_ORIGINAL_DST). We now access the redirect module's API (see APIRequestHandler),
    submit the source information and get the actual destination back (which we stored in 1.1).

    (3) The proxy now establishes the upstream connection as usual.

    (4) Finally, the proxy sends the response back to the client. To make it work, we need to change
    the packet's source address back to the original destination (using the mapping from 1.1),
    to which the client believes it is talking to.

    Limitations:

    - We assume that ephemeral TCP ports are not re-used for multiple connections at the same time.
    The proxy will fail if an application connects to example.com and example.org from
    192.168.0.42:4242 simultaneously. This could be mitigated by introducing unique "meta-addresses"
    which mitmproxy sees, but this would remove the correct client info from mitmproxy.
    """
    local: typing.Optional[RedirectLocal] = None
    # really weird linting error here.
    forward: typing.Optional[Redirect] = None  # noqa
    response: Redirect
    icmp: Redirect

    proxy_port: int
    filter: str

    client_server_map: ClientServerMap

    def __init__(
        self,
        local: bool = True,
        forward: bool = True,
        proxy_port: int = 8080,
        filter: typing.Optional[str] = "tcp.DstPort == 80 or tcp.DstPort == 443",
    ) -> None:
        self.proxy_port = proxy_port
        self.filter = (
            filter
            or
            f"tcp.DstPort != {proxy_port} and tcp.DstPort != {REDIRECT_API_PORT} and tcp.DstPort < 49152"
        )

        self.ipv4_address = get_local_ip()
        self.ipv6_address = get_local_ip6("2001:4860:4860::8888")
        # print(f"IPv4: {self.ipv4_address}, IPv6: {self.ipv6_address}")
        self.client_server_map = ClientServerMap()

        self.api = APIServer(self, (REDIRECT_API_HOST, REDIRECT_API_PORT), APIRequestHandler)
        self.api_thread = threading.Thread(target=self.api.serve_forever)
        self.api_thread.daemon = True

        if forward:
            self.forward = Redirect(
                self.redirect_request,
                self.filter,
                pydivert.Layer.NETWORK_FORWARD
            )
        if local:
            self.local = RedirectLocal(
                self.redirect_request,
                self.filter
            )

        # The proxy server responds to the client. To the client,
        # this response should look like it has been sent by the real target
        self.response = Redirect(
            self.redirect_response,
            f"outbound and tcp.SrcPort == {proxy_port}",
        )

        # Block all ICMP requests (which are sent on Windows by default).
        # If we don't do this, our proxy machine may send an ICMP redirect to the client,
        # which instructs the client to directly connect to the real gateway
        # if they are on the same network.
        self.icmp = Redirect(
            lambda _: None,
            "icmp",
            flags=pydivert.Flag.DROP
        )

    @classmethod
    def setup(cls):
        # TODO: Make sure that server can be killed cleanly. That's a bit difficult as we don't have access to
        # controller.should_exit when this is called.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_unavailable = s.connect_ex((REDIRECT_API_HOST, REDIRECT_API_PORT))
        if server_unavailable:
            proxifier = TransparentProxy()
            proxifier.start()

    def start(self):
        self.api_thread.start()
        self.icmp.start()
        self.response.start()
        if self.forward:
            self.forward.start()
        if self.local:
            self.local.start()

    def shutdown(self):
        if self.local:
            self.local.shutdown()
        if self.forward:
            self.forward.shutdown()
        self.response.shutdown()
        self.icmp.shutdown()
        self.api.shutdown()

    def redirect_request(self, packet: pydivert.Packet):
        # print(" * Redirect client -> server to proxy")
        # print(f"{packet.src_addr}:{packet.src_port} -> {packet.dst_addr}:{packet.dst_port}")
        client = (packet.src_addr, packet.src_port)

        self.client_server_map[client] = (packet.dst_addr, packet.dst_port)

        # We do need to inject to an external IP here, 127.0.0.1 does not work.
        if packet.address_family == socket.AF_INET:
            assert self.ipv4_address
            packet.dst_addr = self.ipv4_address
        elif packet.address_family == socket.AF_INET6:
            if not self.ipv6_address:
                self.ipv6_address = get_local_ip6(packet.src_addr)
            assert self.ipv6_address
            packet.dst_addr = self.ipv6_address
        else:
            raise RuntimeError("Unknown address family")
        packet.dst_port = self.proxy_port
        packet.direction = pydivert.consts.Direction.INBOUND

        # We need a handle on the NETWORK layer. the local handle is not guaranteed to exist,
        # so we use the response handle.
        self.response.windivert.send(packet)

    def redirect_response(self, packet: pydivert.Packet):
        """
        If the proxy responds to the client, let the client believe the target server sent the
        packets.
        """
        # print(" * Adjust proxy -> client")
        client = (packet.dst_addr, packet.dst_port)
        try:
            packet.src_addr, packet.src_port = self.client_server_map[client]
        except KeyError:
            print(f"Warning: Previously unseen connection from proxy to {client}")
        else:
            packet.recalculate_checksums()

        self.response.windivert.send(packet, recalculate_checksum=False)

    @contextlib.contextmanager
    def exempt(self, pid: int):
        if self.local:
            self.local.trusted_pids.add(pid)
        try:
            yield
        finally:
            if self.local:
                self.local.trusted_pids.remove(pid)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--local/--no-local", default=True,
              help="Redirect the host's own traffic.")
@click.option("--forward/--no-forward", default=True,
              help="Redirect traffic that's forwarded by the host.")
@click.option("--filter", type=str, metavar="WINDIVERT_FILTER",
              help="Custom WinDivert interception rule.")
@click.option("-p", "--proxy-port", type=int, metavar="8080", default=8080,
              help="The port mitmproxy is listening on.")
def redirect(**options):
    """Redirect flows to mitmproxy."""
    proxy = TransparentProxy(**options)
    proxy.start()
    print(f" * Redirection active.")
    print(f"   Filter: {proxy.request_filter}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" * Shutting down...")
        proxy.shutdown()
        print(" * Shut down.")


@cli.command()
def connections():
    """List all TCP connections and the associated PIDs."""
    connections = TcpConnectionTable()
    connections.refresh()
    for (ip, port), pid in connections.items():
        print(f"{ip}:{port} -> {pid}")


if __name__ == "__main__":
    cli()
