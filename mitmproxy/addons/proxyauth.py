import binascii
import weakref
import ldap3
from typing import Optional
from typing import MutableMapping  # noqa
from typing import Tuple

import passlib.apache

import mitmproxy.net.http
from mitmproxy import connections  # noqa
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy import ctx
from mitmproxy.net.http import status_codes

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
        self.ldapconn = None
        self.ldapserver = None
        self.authenticated: MutableMapping[connections.ClientConnection, Tuple[str, str]] = weakref.WeakKeyDictionary()
        """Contains all connections that are permanently authenticated after an HTTP CONNECT"""

    def load(self, loader):
        loader.add_option(
            "proxyauth", Optional[str], None,
            """
            Require proxy authentication. Format:
            "username:pass",
            "any" to accept any user/pass combination,
            "@path" to use an Apache htpasswd file,
            or "ldap[s]:url_server_ldap:dn_auth:password:dn_subtree" for LDAP authentication.
            """
        )

    def enabled(self) -> bool:
        return any([self.nonanonymous, self.htpasswd, self.singleuser, self.ldapconn, self.ldapserver])

    def is_proxy_auth(self) -> bool:
        """
        Returns:
            - True, if authentication is done as if mitmproxy is a proxy
            - False, if authentication is done as if mitmproxy is a HTTP server
        """
        return ctx.options.mode == "regular" or ctx.options.mode.startswith("upstream:")

    def which_auth_header(self) -> str:
        if self.is_proxy_auth():
            return 'Proxy-Authorization'
        else:
            return 'Authorization'

    def auth_required_response(self) -> http.HTTPResponse:
        if self.is_proxy_auth():
            return http.make_error_response(
                status_codes.PROXY_AUTH_REQUIRED,
                headers=mitmproxy.net.http.Headers(Proxy_Authenticate='Basic realm="{}"'.format(REALM)),
            )
        else:
            return http.make_error_response(
                status_codes.UNAUTHORIZED,
                headers=mitmproxy.net.http.Headers(WWW_Authenticate='Basic realm="{}"'.format(REALM)),
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
            if self.singleuser == [username, password]:
                return username, password
        elif self.htpasswd:
            if self.htpasswd.check_password(username, password):
                return username, password
        elif self.ldapconn:
            if not username or not password:
                return None
            self.ldapconn.search(ctx.options.proxyauth.split(':')[4], '(cn=' + username + ')')
            if self.ldapconn.response:
                conn = ldap3.Connection(
                    self.ldapserver,
                    self.ldapconn.response[0]['dn'],
                    password,
                    auto_bind=True)
                if conn:
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
    def configure(self, updated):
        if "proxyauth" in updated:
            self.nonanonymous = False
            self.singleuser = None
            self.htpasswd = None
            self.ldapserver = None
            if ctx.options.proxyauth:
                if ctx.options.proxyauth == "any":
                    self.nonanonymous = True
                elif ctx.options.proxyauth.startswith("@"):
                    p = ctx.options.proxyauth[1:]
                    try:
                        self.htpasswd = passlib.apache.HtpasswdFile(p)
                    except (ValueError, OSError):
                        raise exceptions.OptionsError(
                            "Could not open htpasswd file: %s" % p
                        )
                elif ctx.options.proxyauth.startswith("ldap"):
                    parts = ctx.options.proxyauth.split(':')
                    if len(parts) != 5:
                        raise exceptions.OptionsError(
                            "Invalid ldap specification"
                        )
                    security = parts[0]
                    ldap_server = parts[1]
                    dn_baseauth = parts[2]
                    password_baseauth = parts[3]
                    if security == "ldaps":
                        server = ldap3.Server(ldap_server, use_ssl=True)
                    elif security == "ldap":
                        server = ldap3.Server(ldap_server)
                    else:
                        raise exceptions.OptionsError(
                            "Invalid ldap specification on the first part"
                        )
                    conn = ldap3.Connection(
                        server,
                        dn_baseauth,
                        password_baseauth,
                        auto_bind=True)
                    self.ldapconn = conn
                    self.ldapserver = server
                else:
                    parts = ctx.options.proxyauth.split(':')
                    if len(parts) != 2:
                        raise exceptions.OptionsError(
                            "Invalid single-user auth specification."
                        )
                    self.singleuser = parts
        if self.enabled():
            if ctx.options.mode == "transparent":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in transparent mode."
                )
            if ctx.options.mode == "socks5":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in SOCKS mode. "
                    "https://github.com/mitmproxy/mitmproxy/issues/738"
                )
                # TODO: check for multiple auth options

    def http_connect(self, f: http.HTTPFlow) -> None:
        if self.enabled():
            if self.authenticate(f):
                self.authenticated[f.client_conn] = f.metadata["proxyauth"]

    def requestheaders(self, f: http.HTTPFlow) -> None:
        if self.enabled():
            # Is this connection authenticated by a previous HTTP CONNECT?
            if f.client_conn in self.authenticated:
                f.metadata["proxyauth"] = self.authenticated[f.client_conn]
                return
            self.authenticate(f)
