from __future__ import absolute_import, print_function, division

import base64
import collections
import os
import re
from netlib import strutils

import six
from OpenSSL import SSL, crypto

from mitmproxy import exceptions
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

    def __init__(
            self,
            options,
            authenticator=None,
    ):
        self.options = options

        self.authenticator = authenticator

        self.check_ignore = None
        self.check_tcp = None
        self.certstore = None
        self.clientcerts = None
        self.openssl_verification_mode_server = None
        self.configure(options)
        options.changed.connect(self.configure)

    def configure(self, options):
        if options.ssl_verify_upstream_cert:
            self.openssl_verification_mode_server = SSL.VERIFY_PEER
        else:
            self.openssl_verification_mode_server = SSL.VERIFY_NONE

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


def process_proxy_options(parser, options, args):
    if args.add_upstream_certs_to_client_chain and args.ssl_verify_upstream_cert:
        return parser.error(
            "The verify-upstream-cert and add-upstream-certs-to-client-chain "
            "options are mutually exclusive. If upstream certificates are verified "
            "then extra upstream certificates are not available for inclusion "
            "to the client chain."
        )
    if args.auth_nonanonymous or args.auth_singleuser or args.auth_htpasswd:
        if args.transparent_proxy:
            return parser.error("Proxy Authentication not supported in transparent mode.")

        if args.socks_proxy:
            return parser.error(
                "Proxy Authentication not supported in SOCKS mode. "
                "https://github.com/mitmproxy/mitmproxy/issues/738"
            )

        if args.auth_singleuser:
            if len(args.auth_singleuser.split(':')) != 2:
                return parser.error(
                    "Invalid single-user specification. Please use the format username:password"
                )
            username, password = args.auth_singleuser.split(':')
            password_manager = authentication.PassManSingleUser(username, password)
        elif args.auth_nonanonymous:
            password_manager = authentication.PassManNonAnon()
        elif args.auth_htpasswd:
            try:
                password_manager = authentication.PassManHtpasswd(
                    args.auth_htpasswd
                )
            except ValueError as v:
                return parser.error(v)
        authenticator = authentication.BasicProxyAuth(password_manager, "mitmproxy")
    else:
        authenticator = authentication.NullProxyAuth(None)

    return ProxyConfig(
        options,
        authenticator=authenticator,
    )
