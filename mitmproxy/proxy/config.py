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

# We manually need to specify this, otherwise OpenSSL may select a non-HTTP2 cipher by default.
# https://mozilla.github.io/server-side-tls/ssl-config-generator/?server=apache-2.2.15&openssl=1.0.2&hsts=yes&profile=old
DEFAULT_CLIENT_CIPHERS = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:" \
    "ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:" \
    "ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:" \
    "ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:" \
    "DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:" \
    "DHE-RSA-AES256-SHA:ECDHE-RSA-DES-CBC3-SHA:ECDHE-ECDSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:" \
    "AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:DES-CBC3-SHA:" \
    "HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:" \
    "!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA"


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
            no_upstream_cert=False,
            authenticator=None,
            ignore_hosts=tuple(),
            tcp_hosts=tuple(),
            http2=True,
            rawtcp=False,
            ciphers_client=DEFAULT_CLIENT_CIPHERS,
            ciphers_server=None,
            certs=tuple(),
    ):
        self.options = options
        self.ciphers_client = ciphers_client
        self.ciphers_server = ciphers_server
        self.no_upstream_cert = no_upstream_cert

        self.check_ignore = HostMatcher(ignore_hosts)
        self.check_tcp = HostMatcher(tcp_hosts)
        self.http2 = http2
        self.rawtcp = rawtcp
        self.authenticator = authenticator

        self.openssl_method_client, self.openssl_options_client = \
            tcp.sslversion_choices[options.ssl_version_client]
        self.openssl_method_server, self.openssl_options_server = \
            tcp.sslversion_choices[options.ssl_version_server]

        if options.ssl_verify_upstream_cert:
            self.openssl_verification_mode_server = SSL.VERIFY_PEER
        else:
            self.openssl_verification_mode_server = SSL.VERIFY_NONE

        self.certstore = None
        self.clientcerts = None
        self.configure(options)
        options.changed.connect(self.configure)

    def configure(self, options):
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
        no_upstream_cert=args.no_upstream_cert,
        ignore_hosts=args.ignore_hosts,
        tcp_hosts=args.tcp_hosts,
        http2=args.http2,
        rawtcp=args.rawtcp,
        authenticator=authenticator,
        ciphers_client=args.ciphers_client,
        ciphers_server=args.ciphers_server,
    )
