from __future__ import absolute_import, print_function, division

import base64
import collections
import os
import re
from netlib import strutils

import six
from OpenSSL import SSL, crypto

from mitmproxy import exceptions
from mitmproxy import options as moptions  # noqa
from netlib import certutils
from netlib import tcp
from netlib.http import authentication
from netlib.http import url

CONF_BASENAME = "mitmproxy"


class HostMatcher(object):

    def __init__(self, patterns=tuple()):
        self.patterns = list(patterns)
        self.regexes = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def __call__(self, address):
        if not address:
            return False
        address = tcp.Address.wrap(address)
        host = "%s:%s" % (address.host, address.port)
        if any(rex.search(host) for rex in self.regexes):
            return True
        else:
            return False

    def __bool__(self):
        return bool(self.patterns)

    if six.PY2:
        __nonzero__ = __bool__


ServerSpec = collections.namedtuple("ServerSpec", "scheme address")


def parse_server_spec(spec):
    try:
        p = url.parse(spec)
        if p[0] not in (b"http", b"https"):
            raise ValueError()
    except ValueError:
        raise exceptions.OptionsError(
            "Invalid server specification: %s" % spec
        )
    host, port = p[1:3]
    address = tcp.Address((host.decode("ascii"), port))
    scheme = p[0].decode("ascii").lower()
    return ServerSpec(scheme, address)


def parse_upstream_auth(auth):
    pattern = re.compile(".+:")
    if pattern.search(auth) is None:
        raise exceptions.OptionsError(
            "Invalid upstream auth specification: %s" % auth
        )
    return b"Basic" + b" " + base64.b64encode(strutils.always_bytes(auth))


class ProxyConfig:

    def __init__(self, options):
        self.options = options  # type: moptions.Options

        self.authenticator = None
        self.check_ignore = None
        self.check_tcp = None
        self.certstore = None
        self.clientcerts = None
        self.openssl_verification_mode_server = None
        self.configure(options, set(options.keys()))
        options.changed.connect(self.configure)

    def configure(self, options, updated):
        # type: (moptions.Options, Any) -> None
        if options.add_upstream_certs_to_client_chain and not options.ssl_insecure:
            raise exceptions.OptionsError(
                "The verify-upstream-cert requires certificate verification to be disabled. "
                "If upstream certificates are verified then extra upstream certificates are "
                "not available for inclusion to the client chain."
            )

        if options.ssl_insecure:
            self.openssl_verification_mode_server = SSL.VERIFY_NONE
        else:
            self.openssl_verification_mode_server = SSL.VERIFY_PEER

        self.check_ignore = HostMatcher(options.ignore_hosts)
        self.check_tcp = HostMatcher(options.tcp_hosts)

        self.openssl_method_client, self.openssl_options_client = \
            tcp.sslversion_choices[options.ssl_version_client]
        self.openssl_method_server, self.openssl_options_server = \
            tcp.sslversion_choices[options.ssl_version_server]

        certstore_path = os.path.expanduser(options.cadir)
        if not os.path.exists(os.path.dirname(certstore_path)):
            raise exceptions.OptionsError(
                "Certificate Authority parent directory does not exist: %s" %
                os.path.dirname(options.cadir)
            )
        self.certstore = certutils.CertStore.from_store(
            certstore_path,
            CONF_BASENAME
        )

        if options.clientcerts:
            clientcerts = os.path.expanduser(options.clientcerts)
            if not os.path.exists(clientcerts):
                raise exceptions.OptionsError(
                    "Client certificate path does not exist: %s" %
                    options.clientcerts
                )
            self.clientcerts = clientcerts

        for spec, cert in options.certs:
            cert = os.path.expanduser(cert)
            if not os.path.exists(cert):
                raise exceptions.OptionsError(
                    "Certificate file does not exist: %s" % cert
                )
            try:
                self.certstore.add_cert_file(spec, cert)
            except crypto.Error:
                raise exceptions.OptionsError(
                    "Invalid certificate format: %s" % cert
                )

        self.upstream_server = None
        self.upstream_auth = None
        if options.upstream_server:
            self.upstream_server = parse_server_spec(options.upstream_server)
        if options.upstream_auth:
            self.upstream_auth = parse_upstream_auth(options.upstream_auth)

        self.authenticator = authentication.NullProxyAuth(None)
        needsauth = any(
            [
                options.auth_nonanonymous,
                options.auth_singleuser,
                options.auth_htpasswd
            ]
        )
        if needsauth:
            if options.mode == "transparent":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in transparent mode."
                )
            elif options.mode == "socks5":
                raise exceptions.OptionsError(
                    "Proxy Authentication not supported in SOCKS mode. "
                    "https://github.com/mitmproxy/mitmproxy/issues/738"
                )
            elif options.auth_singleuser:
                parts = options.auth_singleuser.split(':')
                if len(parts) != 2:
                    raise exceptions.OptionsError(
                        "Invalid single-user specification. "
                        "Please use the format username:password"
                    )
                password_manager = authentication.PassManSingleUser(*parts)
            elif options.auth_nonanonymous:
                password_manager = authentication.PassManNonAnon()
            elif options.auth_htpasswd:
                try:
                    password_manager = authentication.PassManHtpasswd(
                        options.auth_htpasswd
                    )
                except ValueError as v:
                    raise exceptions.OptionsError(str(v))
            if options.mode == "reverse":
                self.authenticator = authentication.BasicWebsiteAuth(
                    password_manager,
                    self.upstream_server.address
                )
            else:
                self.authenticator = authentication.BasicProxyAuth(
                    password_manager,
                    "mitmproxy"
                )
