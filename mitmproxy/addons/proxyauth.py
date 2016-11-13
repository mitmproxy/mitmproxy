import binascii

import passlib.apache

from mitmproxy import exceptions
from mitmproxy import http
import mitmproxy.net.http


REALM = "mitmproxy"


def mkauth(username, password, scheme="basic"):
    v = binascii.b2a_base64(
        (username + ":" + password).encode("utf8")
    ).decode("ascii")
    return scheme + " " + v


def parse_http_basic_auth(s):
    words = s.split()
    if len(words) != 2:
        return None
    scheme = words[0]
    try:
        user = binascii.a2b_base64(words[1]).decode("utf8", "replace")
    except binascii.Error:
        return None
    parts = user.split(':')
    if len(parts) != 2:
        return None
    return scheme, parts[0], parts[1]


class ProxyAuth:
    def __init__(self):
        self.nonanonymous = False
        self.htpasswd = None
        self.singleuser = None

    def enabled(self):
        return any([self.nonanonymous, self.htpasswd, self.singleuser])

    def which_auth_header(self, f):
        if f.mode == "regular":
            return 'Proxy-Authorization'
        else:
            return 'Authorization'

    def auth_required_response(self, f):
        if f.mode == "regular":
            hdrname = 'Proxy-Authenticate'
        else:
            hdrname = 'WWW-Authenticate'

        headers = mitmproxy.net.http.Headers()
        headers[hdrname] = 'Basic realm="%s"' % REALM

        if f.mode == "transparent":
            return http.make_error_response(
                401,
                "Authentication Required",
                headers
            )
        else:
            return http.make_error_response(
                407,
                "Proxy Authentication Required",
                headers,
            )

    def check(self, f):
        auth_value = f.request.headers.get(self.which_auth_header(f), None)
        if not auth_value:
            return False
        parts = parse_http_basic_auth(auth_value)
        if not parts:
            return False
        scheme, username, password = parts
        if scheme.lower() != 'basic':
            return False

        if self.nonanonymous:
            pass
        elif self.singleuser:
            if [username, password] != self.singleuser:
                return False
        elif self.htpasswd:
            if not self.htpasswd.check_password(username, password):
                return False
        else:
            raise NotImplementedError("Should never happen.")

        return True

    def authenticate(self, f):
        if self.check(f):
            del f.request.headers[self.which_auth_header(f)]
        else:
            f.response = self.auth_required_response(f)

    # Handlers
    def configure(self, options, updated):
        if "auth_nonanonymous" in updated:
            self.nonanonymous = options.auth_nonanonymous
        if "auth_singleuser" in updated:
            if options.auth_singleuser:
                parts = options.auth_singleuser.split(':')
                if len(parts) != 2:
                    raise exceptions.OptionsError(
                        "Invalid single-user auth specification."
                    )
                self.singleuser = parts
            else:
                self.singleuser = None
        if "auth_htpasswd" in updated:
            if options.auth_htpasswd:
                try:
                    self.htpasswd = passlib.apache.HtpasswdFile(
                        options.auth_htpasswd
                    )
                except (ValueError, OSError) as v:
                    raise exceptions.OptionsError(
                        "Could not open htpasswd file: %s" % v
                    )
            else:
                self.htpasswd = None
        if self.enabled():
            if options.mode == "transparent":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in transparent mode."
                )
            elif options.mode == "socks5":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in SOCKS mode. "
                    "https://github.com/mitmproxy/mitmproxy/issues/738"
                )
            # TODO: check for multiple auth options

    def http_connect(self, f):
        if self.enabled() and f.mode == "regular":
            self.authenticate(f)

    def requestheaders(self, f):
        if self.enabled():
            # Are we already authenticated in CONNECT?
            if not (f.mode == "regular" and f.server_conn.via):
                self.authenticate(f)
