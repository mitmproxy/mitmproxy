import time
from typing import Optional, Tuple

from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http, connection
from mitmproxy.net import server_spec
from mitmproxy.net.http import http1
from mitmproxy.proxy import commands, context, layer, tunnel
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

        assert self.tunnel_connection.address
        self.conn.via = server_spec.ServerSpec(
            "https" if self.tunnel_connection.tls else "http",
            self.tunnel_connection.address
        )
        self.buf = ReceiveBuffer()
        self.send_connect = send_connect

    def start_handshake(self) -> layer.CommandGenerator[None]:
        if self.tunnel_connection.tls:
            # "Secure Web Proxy": We may have negotiated an ALPN when connecting to the upstream proxy.
            # The semantics are not really clear here, but we make sure that if we negotiated h2,
            # we act as an h2 client.
            self.conn.alpn = self.tunnel_connection.alpn
        if not self.send_connect:
            return (yield from super().start_handshake())
        assert self.conn.address
        req = http.Request(
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
        raw = http1.assemble_request(req)
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
                yield commands.Log(f"{human.format_address(self.tunnel_connection.address)}: {e}")
                return False, str(e)
            if 200 <= response.status_code < 300:
                if self.buf:
                    yield from self.receive_data(bytes(self.buf))
                    del self.buf
                return True, None
            else:
                raw_resp = b"\n".join(response_head)
                yield commands.Log(f"{human.format_address(self.tunnel_connection.address)}: {raw_resp!r}",
                                   level="debug")
                return False, f"{response.status_code} {response.reason}"
        else:
            return False, None
