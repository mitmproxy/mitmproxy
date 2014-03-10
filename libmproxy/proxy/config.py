import os
from .. import utils, platform
from netlib import http_auth, certutils


TRANSPARENT_SSL_PORTS = [443, 8443]
CONF_BASENAME = "mitmproxy"
CONF_DIR = "~/.mitmproxy"


class ProxyConfig:
    def __init__(self, confdir=CONF_DIR, clientcerts=None,
                       no_upstream_cert=False, body_size_limit=None, upstream_server=None,
                       http_form_in="absolute", http_form_out="relative", transparent_proxy=None, authenticator=None,
                       ciphers=None, certs=None
                ):
        self.ciphers = ciphers
        self.clientcerts = clientcerts
        self.no_upstream_cert = no_upstream_cert
        self.body_size_limit = body_size_limit
        self.upstream_server = upstream_server
        self.http_form_in = http_form_in
        self.http_form_out = http_form_out
        self.transparent_proxy = transparent_proxy
        self.authenticator = authenticator
        self.confdir = os.path.expanduser(confdir)
        self.certstore = certutils.CertStore.from_store(self.confdir, CONF_BASENAME)


def process_proxy_options(parser, options):
    body_size_limit = utils.parse_size(options.body_size_limit)
    if options.reverse_proxy and options.transparent_proxy:
        return parser.error("Can't set both reverse proxy and transparent proxy.")

    if options.transparent_proxy:
        if not platform.resolver:
            return parser.error("Transparent mode not supported on this platform.")
        trans = dict(
            resolver=platform.resolver(),
            sslports=TRANSPARENT_SSL_PORTS
        )
    else:
        trans = None

    if options.reverse_proxy:
        rp = utils.parse_proxy_spec(options.reverse_proxy)
        if not rp:
            return parser.error("Invalid reverse proxy specification: %s" % options.reverse_proxy)
    else:
        rp = None

    if options.forward_proxy:
        fp = utils.parse_proxy_spec(options.forward_proxy)
        if not fp:
            return parser.error("Invalid forward proxy specification: %s" % options.forward_proxy)
    else:
        fp = None

    if options.clientcerts:
        options.clientcerts = os.path.expanduser(options.clientcerts)
        if not os.path.exists(options.clientcerts) or not os.path.isdir(options.clientcerts):
            return parser.error(
                "Client certificate directory does not exist or is not a directory: %s" % options.clientcerts
            )

    if (options.auth_nonanonymous or options.auth_singleuser or options.auth_htpasswd):
        if options.auth_singleuser:
            if len(options.auth_singleuser.split(':')) != 2:
                return parser.error("Invalid single-user specification. Please use the format username:password")
            username, password = options.auth_singleuser.split(':')
            password_manager = http_auth.PassManSingleUser(username, password)
        elif options.auth_nonanonymous:
            password_manager = http_auth.PassManNonAnon()
        elif options.auth_htpasswd:
            try:
                password_manager = http_auth.PassManHtpasswd(options.auth_htpasswd)
            except ValueError, v:
                return parser.error(v.message)
        authenticator = http_auth.BasicProxyAuth(password_manager, "mitmproxy")
    else:
        authenticator = http_auth.NullProxyAuth(None)

    certs = []
    for i in options.certs:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        parts[1] = os.path.expanduser(parts[1])
        if not os.path.exists(parts[1]):
            parser.error("Certificate file does not exist: %s"%parts[1])
        certs.append(parts)

    return ProxyConfig(
        clientcerts=options.clientcerts,
        body_size_limit=body_size_limit,
        no_upstream_cert=options.no_upstream_cert,
        upstream_server=(rp or fp),
        http_form_in=("relative" if (rp or trans) else "absolute"),
        http_form_out=("absolute" if fp else "relative"),
        transparent_proxy=trans,
        authenticator=authenticator,
        ciphers=options.ciphers,
        certs = certs,
    )


def ssl_option_group(parser):
    group = parser.add_argument_group("SSL")
    group.add_argument(
        "--cert", dest='certs', default=[], type=str,
        metavar = "SPEC", action="append",
        help='Add an SSL certificate. SPEC is of the form "[domain=]path". '\
             'The domain may include a wildcard, and is equal to "*" if not specified. '\
             'The file at path is a certificate in PEM format. If a private key is included in the PEM, '\
             'it is used, else the default key in the conf dir is used. Can be passed multiple times.'
    )
    group.add_argument(
        "--client-certs", action="store",
        type=str, dest="clientcerts", default=None,
        help="Client certificate directory."
    )
    group.add_argument(
        "--ciphers", action="store",
        type=str, dest="ciphers", default=None,
        help="SSL cipher specification."
    )