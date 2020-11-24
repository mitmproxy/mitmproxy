from typing import Optional, Tuple

from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http
from mitmproxy.net import server_spec
from mitmproxy.net.http import http1
from mitmproxy.net.http.http1 import read_sansio as http1_sansio
from mitmproxy.proxy2 import commands, context, layer, tunnel
from mitmproxy.utils import human


class HttpUpstreamProxy(tunnel.TunnelLayer):
    buf: ReceiveBuffer
    send_connect: bool
    conn: context.Server
    tunnel_connection: context.Server

    def __init__(
            self,
            ctx: context.Context,
            tunnel_conn: context.Server,
            send_connect: bool
    ):
        super().__init__(
            ctx,
            tunnel_connection=tunnel_conn,
            conn=ctx.server
        )

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
        req = http.make_connect_request(self.conn.address)
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
                response = http1_sansio.read_response_head(response_head)
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
                yield commands.Log(f"{human.format_address(self.tunnel_connection.address)}: {raw_resp}", level="debug")
                return False, f"{response.status_code} {response.reason}"
        else:
            return False, None
