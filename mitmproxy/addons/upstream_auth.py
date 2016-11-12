import re
import base64

from mitmproxy import exceptions
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
        self.root_mode = None

    def configure(self, options, updated):
        # FIXME: We're doing this because our proxy core is terminally confused
        # at the moment. Ideally, we should be able to check if we're in
        # reverse proxy mode at the HTTP layer, so that scripts can put the
        # proxy in reverse proxy mode for specific reuests.
        if "mode" in updated:
            self.root_mode = options.mode
        if "upstream_auth" in updated:
            if options.upstream_auth is None:
                self.auth = None
            else:
                self.auth = parse_upstream_auth(options.upstream_auth)

    def http_connect(self, f):
        if self.auth and f.mode == "upstream":
            f.request.headers["Proxy-Authorization"] = self.auth

    def requestheaders(self, f):
        if self.auth:
            if f.mode == "upstream" and not f.server_conn.via:
                f.request.headers["Proxy-Authorization"] = self.auth
            elif self.root_mode == "reverse":
                f.request.headers["Proxy-Authorization"] = self.auth
