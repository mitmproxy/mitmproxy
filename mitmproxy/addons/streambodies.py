import typing

from mitmproxy.net.http import http1
from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy.utils import human


class StreamBodies:
    def __init__(self):
        self.max_size = None

    def load(self, loader):
        loader.add_option(
            "stream_large_bodies", typing.Optional[str], None,
            """
            Stream data to the client if response body exceeds the given
            threshold. If streamed, the body will not be stored in any way.
            Understands k/m/g suffixes, i.e. 3m for 3 megabytes.
            """
        )
        loader.add_option(
            "stream_websockets", bool, False,
            """
            Stream WebSocket messages between client and server.
            Messages are captured and cannot be modified.
            """
        )

    def configure(self, updated):
        if "stream_large_bodies" in updated and ctx.options.stream_large_bodies:
            try:
                self.max_size = human.parse_size(ctx.options.stream_large_bodies)
            except ValueError as e:
                raise exceptions.OptionsError(e)

    def run(self, f, is_request):
        if self.max_size:
            r = f.request if is_request else f.response
            try:
                expected_size = http1.expected_http_body_size(
                    f.request, f.response if not is_request else None
                )
            except exceptions.HttpException:
                f.reply.kill()
                return
            if expected_size and not r.raw_content and not (0 <= expected_size <= self.max_size):
                # r.stream may already be a callable, which we want to preserve.
                r.stream = r.stream or True
                ctx.log.info("Streaming {} {}".format("response from" if not is_request else "request to", f.request.host))

    def requestheaders(self, f):
        self.run(f, True)

    def responseheaders(self, f):
        self.run(f, False)

    def websocket_start(self, f):
        if ctx.options.stream_websockets:
            f.stream = True
            ctx.log.info("Streaming WebSocket messages between {client} and {server}".format(
                client=human.format_address(f.client_conn.address),
                server=human.format_address(f.server_conn.address))
            )
