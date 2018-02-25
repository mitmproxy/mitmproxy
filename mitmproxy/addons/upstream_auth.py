import re
import typing
import base64

from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy.utils import strutils


def parse_upstream_auth(auth):
    pattern = re.compile(".+:")
    if pattern.search(auth) is None:
        raise exceptions.OptionsError(
            "Invalid upstream auth specification: %s" % auth
        )
    return b"Basic" + b" " + base64.b64encode(strutils.always_bytes(auth))


class UpstreamAuth():
    """
        This addon handles authentication to systems upstream from us for the
        upstream proxy and reverse proxy mode. There are 3 cases:

        - Upstream proxy CONNECT requests should have authentication added, and
          subsequent already connected requests should not.
        - Upstream proxy regular requests
        - Reverse proxy regular requests (CONNECT is invalid in this mode)
    """
    def __init__(self):
        self.auth = None

    def load(self, loader):
        loader.add_option(
            "upstream_auth", typing.Optional[str], None,
            """
            Add HTTP Basic authentication to upstream proxy and reverse proxy
            requests. Format: username:password.
            """
        )

    def configure(self, updated):
        # FIXME: We're doing this because our proxy core is terminally confused
        # at the moment. Ideally, we should be able to check if we're in
        # reverse proxy mode at the HTTP layer, so that scripts can put the
        # proxy in reverse proxy mode for specific requests.
        if "upstream_auth" in updated:
            if ctx.options.upstream_auth is None:
                self.auth = None
            else:
                self.auth = parse_upstream_auth(ctx.options.upstream_auth)

    def http_connect(self, f):
        if self.auth and f.mode == "upstream":
            f.request.headers["Proxy-Authorization"] = self.auth

    def requestheaders(self, f):
        if self.auth:
            if f.mode == "upstream" and not f.server_conn.via:
                f.request.headers["Proxy-Authorization"] = self.auth
            elif ctx.options.mode.startswith("reverse"):
                f.request.headers["Proxy-Authorization"] = self.auth
