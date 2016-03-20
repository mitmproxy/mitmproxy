from __future__ import (absolute_import, print_function, division)
import collections
import os
import re

import six
from OpenSSL import SSL

from netlib import certutils, tcp
from netlib.http import authentication
from netlib.tcp import Address, sslversion_choices

from .. import utils, platform

CONF_BASENAME = "mitmproxy"
CA_DIR = "~/.mitmproxy"

# We manually need to specify this, otherwise OpenSSL may select a non-HTTP2 cipher by default.
# https://mozilla.github.io/server-side-tls/ssl-config-generator/?server=apache-2.2.15&openssl=1.0.2&hsts=yes&profile=old
DEFAULT_CLIENT_CIPHERS = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:ECDHE-RSA-DES-CBC3-SHA:ECDHE-ECDSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:DES-CBC3-SHA:HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA"


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


class ProxyConfig:

    def __init__(
            self,
            host='',
            port=8080,
            cadir=CA_DIR,
            clientcerts=None,
            no_upstream_cert=False,
            body_size_limit=None,
            mode="regular",
            upstream_server=None,
            upstream_auth = None,
            authenticator=None,
            ignore_hosts=tuple(),
            tcp_hosts=tuple(),
            http2=True,
            rawtcp=False,
            ciphers_client=DEFAULT_CLIENT_CIPHERS,
            ciphers_server=None,
            certs=tuple(),
            ssl_version_client="secure",
            ssl_version_server="secure",
            ssl_verify_upstream_cert=False,
            ssl_verify_upstream_trusted_cadir=None,
            ssl_verify_upstream_trusted_ca=None,
            add_upstream_certs_to_client_chain=False,
    ):
        self.host = host
        self.port = port
        self.ciphers_client = ciphers_client
        self.ciphers_server = ciphers_server
        self.clientcerts = clientcerts
        self.no_upstream_cert = no_upstream_cert
        self.body_size_limit = body_size_limit
        self.mode = mode
        if upstream_server:
            self.upstream_server = ServerSpec(upstream_server[0], Address.wrap(upstream_server[1]))
            self.upstream_auth = upstream_auth
        else:
            self.upstream_server = None
            self.upstream_auth = None

        self.check_ignore = HostMatcher(ignore_hosts)
        self.check_tcp = HostMatcher(tcp_hosts)
        self.http2 = http2
        self.rawtcp = rawtcp
        self.authenticator = authenticator
        self.cadir = os.path.expanduser(cadir)
        self.certstore = certutils.CertStore.from_store(
            self.cadir,
            CONF_BASENAME
        )
        for spec, cert in certs:
            self.certstore.add_cert_file(spec, cert)

        self.openssl_method_client, self.openssl_options_client = \
            sslversion_choices[ssl_version_client]
        self.openssl_method_server, self.openssl_options_server = \
            sslversion_choices[ssl_version_server]

        if ssl_verify_upstream_cert:
            self.openssl_verification_mode_server = SSL.VERIFY_PEER
        else:
            self.openssl_verification_mode_server = SSL.VERIFY_NONE
        self.openssl_trusted_cadir_server = ssl_verify_upstream_trusted_cadir
        self.openssl_trusted_ca_server = ssl_verify_upstream_trusted_ca
        self.add_upstream_certs_to_client_chain = add_upstream_certs_to_client_chain


def process_proxy_options(parser, options):
    body_size_limit = utils.parse_size(options.body_size_limit)

    c = 0
    mode, upstream_server, upstream_auth  = "regular", None, None
    if options.transparent_proxy:
        c += 1
        if not platform.resolver:
            return parser.error("Transparent mode not supported on this platform.")
        mode = "transparent"
    if options.socks_proxy:
        c += 1
        mode = "socks5"
    if options.reverse_proxy:
        c += 1
        mode = "reverse"
        upstream_server = options.reverse_proxy
    if options.upstream_proxy:
        c += 1
        mode = "upstream"
        upstream_server = options.upstream_proxy
        upstream_auth = options.upstream_auth
    if c > 1:
        return parser.error(
            "Transparent, SOCKS5, reverse and upstream proxy mode "
            "are mutually exclusive. Read the docs on proxy modes to understand why."
        )
    if options.add_upstream_certs_to_client_chain and options.no_upstream_cert:
        return parser.error(
            "The no-upstream-cert and add-upstream-certs-to-client-chain "
            "options are mutually exclusive. If no-upstream-cert is enabled "
            "then the upstream certificate is not retrieved before generating "
            "the client certificate chain."
        )
    if options.add_upstream_certs_to_client_chain and options.ssl_verify_upstream_cert:
        return parser.error(
            "The verify-upstream-cert and add-upstream-certs-to-client-chain "
            "options are mutually exclusive. If upstream certificates are verified "
            "then extra upstream certificates are not available for inclusion "
            "to the client chain."
        )
    if options.clientcerts:
        options.clientcerts = os.path.expanduser(options.clientcerts)
        if not os.path.exists(options.clientcerts):
            return parser.error(
                    "Client certificate path does not exist: %s" % options.clientcerts
            )
    if options.auth_nonanonymous or options.auth_singleuser or options.auth_htpasswd:

        if options.transparent_proxy:
            return parser.error("Proxy Authentication not supported in transparent mode.")

        if options.socks_proxy:
            return parser.error(
                "Proxy Authentication not supported in SOCKS mode. "
                "https://github.com/mitmproxy/mitmproxy/issues/738"
            )

        if options.auth_singleuser:
            if len(options.auth_singleuser.split(':')) != 2:
                return parser.error(
                    "Invalid single-user specification. Please use the format username:password"
                )
            username, password = options.auth_singleuser.split(':')
            password_manager = authentication.PassManSingleUser(username, password)
        elif options.auth_nonanonymous:
            password_manager = authentication.PassManNonAnon()
        elif options.auth_htpasswd:
            try:
                password_manager = authentication.PassManHtpasswd(
                    options.auth_htpasswd)
            except ValueError as v:
                return parser.error(v.message)
        authenticator = authentication.BasicProxyAuth(password_manager, "mitmproxy")
    else:
        authenticator = authentication.NullProxyAuth(None)

    certs = []
    for i in options.certs:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        parts[1] = os.path.expanduser(parts[1])
        if not os.path.exists(parts[1]):
            parser.error("Certificate file does not exist: %s" % parts[1])
        certs.append(parts)

    return ProxyConfig(
        host=options.addr,
        port=options.port,
        cadir=options.cadir,
        clientcerts=options.clientcerts,
        no_upstream_cert=options.no_upstream_cert,
        body_size_limit=body_size_limit,
        mode=mode,
        upstream_server=upstream_server,
        upstream_auth=upstream_auth,
        ignore_hosts=options.ignore_hosts,
        tcp_hosts=options.tcp_hosts,
        http2=options.http2,
        rawtcp=options.rawtcp,
        authenticator=authenticator,
        ciphers_client=options.ciphers_client,
        ciphers_server=options.ciphers_server,
        certs=tuple(certs),
        ssl_version_client=options.ssl_version_client,
        ssl_version_server=options.ssl_version_server,
        ssl_verify_upstream_cert=options.ssl_verify_upstream_cert,
        ssl_verify_upstream_trusted_cadir=options.ssl_verify_upstream_trusted_cadir,
        ssl_verify_upstream_trusted_ca=options.ssl_verify_upstream_trusted_ca,
        add_upstream_certs_to_client_chain=options.add_upstream_certs_to_client_chain,
    )
