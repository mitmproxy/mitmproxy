from mitmproxy.net.http import http1
from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy.utils import human


class StreamBodies:
    def __init__(self):
        self.max_size = None

    def configure(self, options, updated):
        if "stream_large_bodies" in updated and options.stream_large_bodies:
            try:
                self.max_size = human.parse_size(options.stream_large_bodies)
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
                # FIXME: make message generic when we add rquest streaming
                ctx.log.info("Streaming response from %s" % f.request.host)

    # FIXME! Request streaming doesn't work at the moment.
    def requestheaders(self, f):
        self.run(f, True)

    def responseheaders(self, f):
        self.run(f, False)
