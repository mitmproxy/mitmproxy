import base64
import re
from typing import Optional

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy.proxy import mode_specs
from mitmproxy.utils import strutils


def parse_upstream_auth(auth: str) -> bytes:
    pattern = re.compile(".+:")
    if pattern.search(auth) is None:
        raise exceptions.OptionsError("Invalid upstream auth specification: %s" % auth)
    return b"Basic" + b" " + base64.b64encode(strutils.always_bytes(auth))


class UpstreamAuth:
    """
    This addon handles authentication to systems upstream from us for the
    upstream proxy and reverse proxy mode. There are 3 cases:

    - Upstream proxy CONNECT requests should have authentication added, and
      subsequent already connected requests should not.
    - Upstream proxy regular requests
    - Reverse proxy regular requests (CONNECT is invalid in this mode)
    """

    auth: bytes | None = None

    def load(self, loader):
        loader.add_option(
            "upstream_auth",
            Optional[str],
            None,
            """
            Add HTTP Basic authentication to upstream proxy and reverse proxy
            requests. Format: username:password.
            """,
        )

    def configure(self, updated):
        if "upstream_auth" in updated:
            if ctx.options.upstream_auth is None:
                self.auth = None
            else:
                self.auth = parse_upstream_auth(ctx.options.upstream_auth)

    def http_connect_upstream(self, f: http.HTTPFlow):
        if self.auth:
            f.request.headers["Proxy-Authorization"] = self.auth

    def requestheaders(self, f: http.HTTPFlow):
        if self.auth:
            if (
                isinstance(f.client_conn.proxy_mode, mode_specs.UpstreamMode)
                and f.request.scheme == "http"
            ):
                f.request.headers["Proxy-Authorization"] = self.auth
            elif isinstance(f.client_conn.proxy_mode, mode_specs.ReverseMode):
                f.request.headers["Authorization"] = self.auth
