import binascii
import weakref
from typing import Optional
from typing import Set  # noqa
from typing import Tuple

import passlib.apache

import mitmproxy.net.http
from mitmproxy import connections  # noqa
from mitmproxy import exceptions
from mitmproxy import http

REALM = "mitmproxy"


def mkauth(username: str, password: str, scheme: str = "basic") -> str:
    """
    Craft a basic auth string
    """
    v = binascii.b2a_base64(
        (username + ":" + password).encode("utf8")
    ).decode("ascii")
    return scheme + " " + v


def parse_http_basic_auth(s: str) -> Tuple[str, str, str]:
    """
    Parse a basic auth header.
    Raises a ValueError if the input is invalid.
    """
    scheme, authinfo = s.split()
    if scheme.lower() != "basic":
        raise ValueError("Unknown scheme")
    try:
        user, password = binascii.a2b_base64(authinfo.encode()).decode("utf8", "replace").split(":")
    except binascii.Error as e:
        raise ValueError(str(e))
    return scheme, user, password


class ProxyAuth:
    def __init__(self):
        self.nonanonymous = False
        self.htpasswd = None
        self.singleuser = None
        self.mode = None
        self.authenticated = weakref.WeakSet()  # type: Set[connections.ClientConnection]
        """Contains all connections that are permanently authenticated after an HTTP CONNECT"""

    def enabled(self) -> bool:
        return any([self.nonanonymous, self.htpasswd, self.singleuser])

    def is_proxy_auth(self) -> bool:
        """
        Returns:
            - True, if authentication is done as if mitmproxy is a proxy
            - False, if authentication is done as if mitmproxy is a HTTP server
        """
        return self.mode in ("regular", "upstream")

    def which_auth_header(self) -> str:
        if self.is_proxy_auth():
            return 'Proxy-Authorization'
        else:
            return 'Authorization'

    def auth_required_response(self) -> http.HTTPResponse:
        if self.is_proxy_auth():
            return http.make_error_response(
                407,
                "Proxy Authentication Required",
                mitmproxy.net.http.Headers(Proxy_Authenticate='Basic realm="{}"'.format(REALM)),
            )
        else:
            return http.make_error_response(
                401,
                "Authentication Required",
                mitmproxy.net.http.Headers(WWW_Authenticate='Basic realm="{}"'.format(REALM)),
            )

    def check(self, f: http.HTTPFlow) -> Optional[Tuple[str, str]]:
        """
        Check if a request is correctly authenticated.
        Returns:
            - a (username, password) tuple if successful,
            - None, otherwise.
        """
        auth_value = f.request.headers.get(self.which_auth_header(), "")
        try:
            scheme, username, password = parse_http_basic_auth(auth_value)
        except ValueError:
            return None

        if self.nonanonymous:
            return username, password
        elif self.singleuser:
            if [username, password] == self.singleuser:
                return username, password
        elif self.htpasswd:
            if self.htpasswd.check_password(username, password):
                return username, password

        return None

    def authenticate(self, f: http.HTTPFlow) -> bool:
        valid_credentials = self.check(f)
        if valid_credentials:
            f.metadata["proxyauth"] = valid_credentials
            del f.request.headers[self.which_auth_header()]
            return True
        else:
            f.response = self.auth_required_response()
            return False

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
        if "mode" in updated:
            self.mode = options.mode
        if self.enabled():
            if options.mode == "transparent":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in transparent mode."
                )
            if options.mode == "socks5":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in SOCKS mode. "
                    "https://github.com/mitmproxy/mitmproxy/issues/738"
                )
                # TODO: check for multiple auth options

    def http_connect(self, f: http.HTTPFlow) -> None:
        if self.enabled():
            if self.authenticate(f):
                self.authenticated.add(f.client_conn)

    def requestheaders(self, f: http.HTTPFlow) -> None:
        if self.enabled():
            # Is this connection authenticated by a previous HTTP CONNECT?
            if f.client_conn in self.authenticated:
                return
            self.authenticate(f)
