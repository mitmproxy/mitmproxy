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


class UpstreamProxyAuth():
    def __init__(self):
        self.auth = None

    def configure(self, options, updated):
        if "upstream_auth" in updated:
            if options.upstream_auth is None:
                self.auth = None
            else:
                self.auth = parse_upstream_auth(options.upstream_auth)

    def requestheaders(self, f):
        if self.auth and f.mode == "upstream":
            f.request.headers["Proxy-Authorization"] = self.auth
