from __future__ import annotations

import binascii
import weakref
from abc import ABC, abstractmethod
from typing import MutableMapping
from typing import Optional
from typing import Tuple

import ldap3
import passlib.apache

from mitmproxy import connection, ctx
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy.net.http import status_codes
from mitmproxy.proxy.layers import modes

REALM = "mitmproxy"


class ProxyAuth:
    validator: Optional[Validator] = None

    def __init__(self):
        self.authenticated: MutableMapping[connection.Client, Tuple[str, str]] = weakref.WeakKeyDictionary()
        """Contains all connections that are permanently authenticated after an HTTP CONNECT"""

    def load(self, loader):
        loader.add_option(
            "proxyauth", Optional[str], None,
            """
            Require proxy authentication. Format:
            "username:pass",
            "any" to accept any user/pass combination,
            "@path" to use an Apache htpasswd file,
            or "ldap[s]:url_server_ldap[:port]:dn_auth:password:dn_subtree" for LDAP authentication.
            """
        )

    def configure(self, updated):
        if "proxyauth" not in updated:
            return
        auth = ctx.options.proxyauth
        if auth:
            if ctx.options.mode == "transparent":
                raise exceptions.OptionsError("Proxy Authentication not supported in transparent mode.")

            if auth == "any":
                self.validator = AcceptAll()
            elif auth.startswith("@"):
                self.validator = Htpasswd(auth)
            elif ctx.options.proxyauth.startswith("ldap"):
                self.validator = Ldap(auth)
            elif ":" in ctx.options.proxyauth:
                self.validator = SingleUser(auth)
            else:
                raise exceptions.OptionsError("Invalid proxyauth specification.")
        else:
            self.validator = None

    def socks5_auth(self, data: modes.Socks5AuthData) -> None:
        if self.validator and self.validator(data.username, data.password):
            data.valid = True
            self.authenticated[data.client_conn] = data.username, data.password

    def http_connect(self, f: http.HTTPFlow) -> None:
        if self.validator and self.authenticate_http(f):
            # Make a note that all further requests over this connection are ok.
            self.authenticated[f.client_conn] = f.metadata["proxyauth"]

    def requestheaders(self, f: http.HTTPFlow) -> None:
        if self.validator:
            # Is this connection authenticated by a previous HTTP CONNECT?
            if f.client_conn in self.authenticated:
                f.metadata["proxyauth"] = self.authenticated[f.client_conn]
            else:
                self.authenticate_http(f)

    def authenticate_http(self, f: http.HTTPFlow) -> bool:
        """
        Authenticate an HTTP request, returns if authentication was successful.

        If valid credentials are found, the matching authentication header is removed.
        In no or invalid credentials are found, flow.response is set to an error page.
        """
        assert self.validator
        username = None
        password = None
        is_valid = False
        try:
            auth_value = f.request.headers.get(self.http_auth_header, "")
            scheme, username, password = parse_http_basic_auth(auth_value)
            is_valid = self.validator(username, password)
        except Exception:
            pass

        if is_valid:
            f.metadata["proxyauth"] = (username, password)
            del f.request.headers[self.http_auth_header]
            return True
        else:
            f.response = self.make_auth_required_response()
            return False

    def make_auth_required_response(self) -> http.Response:
        if self.is_http_proxy:
            status_code = status_codes.PROXY_AUTH_REQUIRED
            headers = {"Proxy-Authenticate": f'Basic realm="{REALM}"'}
        else:
            status_code = status_codes.UNAUTHORIZED
            headers = {"WWW-Authenticate": f'Basic realm="{REALM}"'}

        reason = http.status_codes.RESPONSES[status_code]
        return http.Response.make(
            status_code,
            (
                f"<html>"
                f"<head><title>{status_code} {reason}</title></head>"
                f"<body><h1>{status_code} {reason}</h1></body>"
                f"</html>"
            ),
            headers
        )

    @property
    def http_auth_header(self) -> str:
        if self.is_http_proxy:
            return "Proxy-Authorization"
        else:
            return "Authorization"

    @property
    def is_http_proxy(self) -> bool:
        """
        Returns:
            - True, if authentication is done as if mitmproxy is a proxy
            - False, if authentication is done as if mitmproxy is an HTTP server
        """
        return ctx.options.mode == "regular" or ctx.options.mode.startswith("upstream:")


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


class Validator(ABC):
    """Base class for all username/password validators."""

    @abstractmethod
    def __call__(self, username: str, password: str) -> bool:
        raise NotImplementedError


class AcceptAll(Validator):
    def __call__(self, username: str, password: str) -> bool:
        return True


class SingleUser(Validator):
    def __init__(self, proxyauth: str):
        try:
            self.username, self.password = proxyauth.split(':')
        except ValueError:
            raise exceptions.OptionsError("Invalid single-user auth specification.")

    def __call__(self, username: str, password: str) -> bool:
        return self.username == username and self.password == password


class Htpasswd(Validator):
    def __init__(self, proxyauth: str):
        path = proxyauth[1:]
        try:
            self.htpasswd = passlib.apache.HtpasswdFile(path)
        except (ValueError, OSError):
            raise exceptions.OptionsError(f"Could not open htpasswd file: {path}")

    def __call__(self, username: str, password: str) -> bool:
        return self.htpasswd.check_password(username, password)


class Ldap(Validator):
    conn: ldap3.Connection
    server: ldap3.Server
    dn_subtree: str

    def __init__(self, proxyauth: str):
        (
            use_ssl,
            url,
            port,
            ldap_user,
            ldap_pass,
            self.dn_subtree,
        ) = self.parse_spec(proxyauth)
        server = ldap3.Server(url, port=port, use_ssl=use_ssl)
        conn = ldap3.Connection(
            server,
            ldap_user,
            ldap_pass,
            auto_bind=True
        )
        self.conn = conn
        self.server = server

    @staticmethod
    def parse_spec(spec: str) -> Tuple[bool, str, Optional[int], str, str, str]:
        try:
            if spec.count(":") > 4:
                (
                    security,
                    url,
                    port_str,
                    ldap_user,
                    ldap_pass,
                    dn_subtree,
                ) = spec.split(":")
                port = int(port_str)
            else:
                security, url, ldap_user, ldap_pass, dn_subtree = spec.split(":")
                port = None

            if security == "ldaps":
                use_ssl = True
            elif security == "ldap":
                use_ssl = False
            else:
                raise ValueError

            return use_ssl, url, port, ldap_user, ldap_pass, dn_subtree
        except ValueError:
            raise exceptions.OptionsError(f"Invalid LDAP specification: {spec}")

    def __call__(self, username: str, password: str) -> bool:
        if not username or not password:
            return False
        self.conn.search(self.dn_subtree, f"(cn={username})")
        if self.conn.response:
            c = ldap3.Connection(
                self.server,
                self.conn.response[0]["dn"],
                password,
                auto_bind=True
            )
            if c:
                return True
        return False
