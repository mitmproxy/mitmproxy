import sys
import argparse
import os
import os.path
import re

from netlib import tcp
from netlib import human
from netlib import version
from . import pathod


def parse_anchor_spec(s):
    """
        Return a tuple, or None on error.
    """
    if "=" not in s:
        return None
    return tuple(s.split("=", 1))


def args_pathod(argv, stdout_=sys.stdout, stderr_=sys.stderr):
    parser = argparse.ArgumentParser(
        description='A pathological HTTP/S daemon.'
    )
    parser.add_argument(
        '--version',
        action='version',
        version="pathod " + version.VERSION
    )
    parser.add_argument(
        "-p",
        dest='port',
        default=9999,
        type=int,
        help='Port. Specify 0 to pick an arbitrary empty port. (9999)'
    )
    parser.add_argument(
        "-l",
        dest='address',
        default="127.0.0.1",
        type=str,
        help='Listening address. (127.0.0.1)'
    )
    parser.add_argument(
        "-a",
        dest='anchors',
        default=[],
        type=str,
        action="append",
        metavar="ANCHOR",
        help="""
            Add an anchor. Specified as a string with the form
            pattern=spec or pattern=filepath, where pattern is a regular
            expression.
        """
    )
    parser.add_argument(
        "-c", dest='craftanchor', default=pathod.DEFAULT_CRAFT_ANCHOR, type=str,
        help="""
            URL path specifying prefix for URL crafting
            commands. (%s)
        """ % pathod.DEFAULT_CRAFT_ANCHOR
    )
    parser.add_argument(
        "--confdir",
        action="store", type=str, dest="confdir", default='~/.mitmproxy',
        help="Configuration directory. (~/.mitmproxy)"
    )
    parser.add_argument(
        "-d", dest='staticdir', default=None, type=str,
        help='Directory for static files.'
    )
    parser.add_argument(
        "-D", dest='daemonize', default=False, action="store_true",
        help='Daemonize.'
    )
    parser.add_argument(
        "-t", dest="timeout", type=int, default=None,
        help="Connection timeout"
    )
    parser.add_argument(
        "--limit-size",
        dest='sizelimit',
        default=None,
        type=str,
        help='Size limit of served responses. Understands size suffixes, i.e. 100k.')
    parser.add_argument(
        "--nohang", dest='nohang', default=False, action="store_true",
        help='Disable pauses during crafted response generation.'
    )
    parser.add_argument(
        "--nocraft",
        dest='nocraft',
        default=False,
        action="store_true",
        help='Disable response crafting. If anchors are specified, they still work.')
    parser.add_argument(
        "--webdebug", dest='webdebug', default=False, action="store_true",
        help='Debugging mode for the web app (dev only).'
    )

    group = parser.add_argument_group(
        'SSL',
    )
    group.add_argument(
        "-s", dest='ssl', default=False, action="store_true",
        help='Run in HTTPS mode.'
    )
    group.add_argument(
        "--cn",
        dest="cn",
        type=str,
        default=None,
        help="CN for generated SSL certs. Default: %s" %
        pathod.DEFAULT_CERT_DOMAIN)
    group.add_argument(
        "-C", dest='ssl_not_after_connect', default=False, action="store_true",
        help="Don't expect SSL after a CONNECT request."
    )
    group.add_argument(
        "--cert", dest='ssl_certs', default=[], type=str,
        metavar="SPEC", action="append",
        help="""
        Add an SSL certificate. SPEC is of the form "[domain=]path". The domain
        may include a wildcard, and is equal to "*" if not specified. The file
        at path is a certificate in PEM format. If a private key is included in
        the PEM, it is used, else the default key in the conf dir is used. Can
        be passed multiple times.
        """
    )
    group.add_argument(
        "--ciphers", dest="ciphers", type=str, default=False,
        help="SSL cipher specification"
    )
    group.add_argument(
        "--san", dest="sans", type=str, default=[], action="append",
        metavar="SAN",
        help="""
            Subject Altnernate Name to add to the server certificate.
            May be passed multiple times.
        """
    )
    group.add_argument(
        "--ssl-version", dest="ssl_version", type=str, default="secure",
        choices=tcp.sslversion_choices.keys(),
        help="Set supported SSL/TLS versions. "
             "SSLv2, SSLv3 and 'all' are INSECURE. Defaults to secure, which is TLS1.0+."
    )

    group = parser.add_argument_group(
        'Controlling Logging',
        """
            Some of these options expand generated values for logging - if
            you're generating large data, use them with caution.
        """
    )
    group.add_argument(
        "-e", dest="explain", action="store_true", default=False,
        help="Explain responses"
    )
    group.add_argument(
        "-f", dest='logfile', default=None, type=str,
        help='Log to file.'
    )
    group.add_argument(
        "-q", dest="logreq", action="store_true", default=False,
        help="Log full request"
    )
    group.add_argument(
        "-r", dest="logresp", action="store_true", default=False,
        help="Log full response"
    )
    group.add_argument(
        "-x", dest="hexdump", action="store_true", default=False,
        help="Log request/response in hexdump format"
    )
    group.add_argument(
        "--http2-framedump", dest="http2_framedump", action="store_true", default=False,
        help="Output all received & sent HTTP/2 frames"
    )

    args = parser.parse_args(argv[1:])

    args.ssl_version, args.ssl_options = tcp.sslversion_choices[args.ssl_version]

    certs = []
    for i in args.ssl_certs:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        parts[1] = os.path.expanduser(parts[1])
        if not os.path.isfile(parts[1]):
            return parser.error(
                "Certificate file does not exist: %s" %
                parts[1])
        certs.append(parts)
    args.ssl_certs = certs

    alst = []
    for i in args.anchors:
        parts = parse_anchor_spec(i)
        if not parts:
            return parser.error("Invalid anchor specification: %s" % i)
        alst.append(parts)
    args.anchors = alst

    sizelimit = None
    if args.sizelimit:
        try:
            sizelimit = human.parse_size(args.sizelimit)
        except ValueError as v:
            return parser.error(v)
    args.sizelimit = sizelimit

    anchors = []
    for patt, spec in args.anchors:
        if os.path.isfile(spec):
            data = open(spec).read()
            spec = data
        try:
            arex = re.compile(patt)
        except re.error:
            return parser.error("Invalid regex in anchor: %s" % patt)
        anchors.append((arex, spec))
    args.anchors = anchors

    return args


def go_pathod():  # pragma: no cover
    args = args_pathod(sys.argv)
    pathod.main(args)
