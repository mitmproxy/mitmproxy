import time
from typing import Optional, Tuple

from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http, connection
from mitmproxy.net.http import http1
from mitmproxy.proxy import commands, context, layer, tunnel
from mitmproxy.proxy.layers.http._hooks import HttpConnectUpstreamHook
from mitmproxy.proxy.layers import tls
from mitmproxy.utils import human


class HttpUpstreamProxy(tunnel.TunnelLayer):
    buf: ReceiveBuffer
    send_connect: bool
    conn: connection.Server
    tunnel_connection: connection.Server

    def __init__(
            self,
            ctx: context.Context,
            tunnel_conn: connection.Server,
            send_connect: bool
    ):
        super().__init__(
            ctx,
            tunnel_connection=tunnel_conn,
            conn=ctx.server
        )
        self.buf = ReceiveBuffer()
        self.send_connect = send_connect

    @classmethod
    def make(cls, ctx: context.Context, send_connect: bool) -> tunnel.LayerStack:
        spec = ctx.server.via
        assert spec
        assert spec.scheme in ("http", "https")

        http_proxy = connection.Server(spec.address)

        stack = tunnel.LayerStack()
        if spec.scheme == "https":
            http_proxy.alpn_offers = tls.HTTP1_ALPNS
            http_proxy.sni = spec.address[0]
            stack /= tls.ServerTLSLayer(ctx, http_proxy)
        stack /= cls(ctx, http_proxy, send_connect)

        return stack

    def start_handshake(self) -> layer.CommandGenerator[None]:
        if not self.send_connect:
            return (yield from super().start_handshake())
        assert self.conn.address
        flow = http.HTTPFlow(self.context.client, self.tunnel_connection)
        flow.request = http.Request(
            host=self.conn.address[0],
            port=self.conn.address[1],
            method=b"CONNECT",
            scheme=b"",
            authority=f"{self.conn.address[0]}:{self.conn.address[1]}".encode(),
            path=b"",
            http_version=b"HTTP/1.1",
            headers=http.Headers(),
            content=b"",
            trailers=None,
            timestamp_start=time.time(),
            timestamp_end=time.time(),
        )
        yield HttpConnectUpstreamHook(flow)
        raw = http1.assemble_request(flow.request)
        yield commands.SendData(self.tunnel_connection, raw)

    def receive_handshake_data(self, data: bytes) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        if not self.send_connect:
            return (yield from super().receive_handshake_data(data))
        self.buf += data
        response_head = self.buf.maybe_extract_lines()
        if response_head:
            response_head = [bytes(x) for x in response_head]  # TODO: Make url.parse compatible with bytearrays
            try:
                response = http1.read_response_head(response_head)
            except ValueError as e:
                proxyaddr = human.format_address(self.tunnel_connection.address)
                yield commands.Log(f"{proxyaddr}: {e}")
                return False, f"Error connecting to {proxyaddr}: {e}"
            if 200 <= response.status_code < 300:
                if self.buf:
                    yield from self.receive_data(bytes(self.buf))
                    del self.buf
                return True, None
            else:
                proxyaddr = human.format_address(self.tunnel_connection.address)
                raw_resp = b"\n".join(response_head)
                yield commands.Log(f"{proxyaddr}: {raw_resp!r}",
                                   level="debug")
                return False, f"Upstream proxy {proxyaddr} refused HTTP CONNECT request: {response.status_code} {response.reason}"
        else:
            return False, None
