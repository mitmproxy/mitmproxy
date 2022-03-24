import asyncio
from typing import Dict, List, Optional, Tuple
from mitmproxy import ctx, flow, log, master, options, platform
from mitmproxy.addonmanager import Loader
from mitmproxy.connection import ConnectionProtocol
from mitmproxy.net import udp
from mitmproxy.proxy import commands, layers, server, server_hooks
from mitmproxy.utils import asyncio_utils, human


# almost same as/copied from ProxyConnectionHandler
# TODO introduce base class AddonConnectionHandler
class DnsConnectionHandler(server.StreamConnectionHandler):
    def __init__(self, master: master.Master, r: asyncio.StreamReader, w: asyncio.StreamWriter, options: options.Options):
        self.master = master
        super().__init__(r, w, options)
        self.log_prefix = f"[DNS] {human.format_address(self.client.peername)}: "
        self.layer = layers.DNSLayer(self.layer.context)

    async def handle_hook(self, hook: commands.StartHook) -> None:
        with self.timeout_watchdog.disarm():
            # We currently only support single-argument hooks.
            data, = hook.args()
            await self.master.addons.handle_lifecycle(hook)
            if isinstance(data, flow.Flow):
                await data.wait_for_resume()

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(self.log_prefix + message, level)
        asyncio_utils.create_task(
            self.master.addons.handle_lifecycle(log.AddLogHook(x)),
            name="DnsConnectionHandler.log"
        )


# very similar to/copied from Proxyserver
# TODO introduce base class AddonServer
class DnsServer:
    """
    This addon runs the DNS server.
    """
    _lock: asyncio.Lock
    _connections: Dict[Tuple, DnsConnectionHandler]
    server: Optional[asyncio.AbstractServer]
    master: master.Master
    options: options.Options
    is_running: bool

    def __init__(self):
        self._lock = asyncio.Lock()
        self._connections = {}
        self.server = None
        self.is_running = False

    def __repr__(self) -> str:
        return f"DnsServer({'running' if self.server else 'stopped'}, {len(self._connections)} active conns)"

    def load(self, loader: Loader) -> None:
        loader.add_option(
            "dns_server", bool, False,
            """Start a DNS server. Disabled by default."""
        )
        loader.add_option(
            "dns_listen_host", Optional[str], "",
            """Address to bind DNS server to."""
        )
        loader.add_option(
            "dns_listen_port", int, 53,
            """DNS server service port."""
        )
        loader.add_option(
            "dns_mode", str, "simple",
            """DNS mode can be "simple", "forward:<ip>[:<port>]" or "transparent".""",
        )

    def configure(self, updated: List[str], *, force_refresh: bool = False) -> None:
        if "dns_mode" in updated and ctx.options.dns_mode == "transparent":
            platform.init_transparent_mode()
        if not self.is_running:
            return
        if force_refresh or any(x.startswith('dns_') for x in updated):
            asyncio.create_task(self.refresh_server())

    def running(self) -> None:
        self.master = ctx.master
        self.options = ctx.options
        self.is_running = True
        self.configure([], force_refresh=True)

    async def refresh_server(self) -> None:
        async with self._lock:
            if self.server:
                await self.shutdown_server()
                self.server = None
            if ctx.options.dns_server:
                self.server = await udp.start_server(
                    self.handle_connection,
                    self.options.dns_listen_host,
                    self.options.dns_listen_port,
                    transparent=ctx.options.dns_mode == "transparent",
                )
                addrs = {human.format_address(s.getsockname()) for s in self.server.sockets}
                ctx.log.info(f"DNS server listening at {' and '.join(addrs)}")

    async def shutdown_server(self) -> None:
        ctx.log.info("Stopping server...")
        self.server.close()
        await self.server.wait_closed()
        self.server = None

    async def handle_connection(self, r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        peername = w.get_extra_info('peername')
        asyncio_utils.set_task_debug_info(
            asyncio.current_task(),
            name=f"DnsServer.handle_connection",
            client=peername,
        )
        handler = DnsConnectionHandler(self.master, r, w, self.options)
        self._connections[peername] = handler
        try:
            await handler.handle_client()
        finally:
            del self._connections[peername]

    def server_connect(self, ctx: server_hooks.ServerConnectionHookData) -> None:
        assert ctx.server.address
        self_connect = (
            ctx.server.protocol == ConnectionProtocol.UDP
            and
            ctx.server.address[1] == self.options.dns_listen_port
            and
            ctx.server.address[0] in ("localhost", "127.0.0.1", "::1", self.options.dns_listen_host)
        )
        if self_connect:
            ctx.server.error = "Stopped mitmproxy from recursively connecting to itself."
