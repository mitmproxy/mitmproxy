#!/usr/bin/env python
import argparse
import sys
import os
from . import pathoc, pathod, version, utils
from netlib import http_uastrings


def go_pathoc():
    preparser = argparse.ArgumentParser(add_help=False)
    preparser.add_argument(
        "--show-uas", dest="showua", action="store_true", default=False,
        help="Print user agent shortcuts and exit."
    )
    pa = preparser.parse_known_args()[0]
    if pa.showua:
        print "User agent strings:"
        for i in http_uastrings.UASTRINGS:
            print "  ", i[1], i[0]
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description='A perverse HTTP client.', parents=[preparser]
    )
    parser.add_argument(
        '--version',
        action='version',
        version="pathoc " + version.VERSION
    )
    parser.add_argument(
        "-c", dest="connect_to", type=str, default=False,
        metavar = "HOST:PORT",
        help="Issue an HTTP CONNECT to connect to the specified host."
    )
    parser.add_argument(
        "-n", dest='repeat', default=1, type=int, metavar="N",
        help='Repeat requests N times'
    )
    parser.add_argument(
        "-p", dest="port", type=int, default=None,
        help="Port. Defaults to 80, or 443 if SSL is active"
    )
    parser.add_argument(
        "-t", dest="timeout", type=int, default=None,
        help="Connection timeout"
    )
    parser.add_argument(
        'host', type=str,
        help='Host to connect to'
    )
    parser.add_argument(
        'request', type=str, nargs="+",
        help='Request specification'
    )

    group = parser.add_argument_group(
        'SSL',
    )
    group.add_argument(
        "-s", dest="ssl", action="store_true", default=False,
        help="Connect with SSL"
    )
    group.add_argument(
        "-C", dest="clientcert", type=str, default=False,
        help="Path to a file containing client certificate and private key"
    )
    group.add_argument(
        "-i", dest="sni", type=str, default=False,
        help="SSL Server Name Indication"
    )
    group.add_argument(
        "--ciphers", dest="ciphers", type=str, default=False,
        help="SSL cipher specification"
    )
    group.add_argument(
        "--sslversion", dest="sslversion", type=int, default=4,
        choices=[1, 2, 3, 4],
        help="Use a specified protocol - TLSv1, SSLv2, SSLv3, SSLv23. Default to SSLv23."
    )

    group = parser.add_argument_group(
        'Controlling Output',
        """
            Some of these options expand generated values for logging - if
            you're generating large data, use them with caution.
        """
    )
    group.add_argument(
        "-I", dest="ignorecodes", type=str, default="",
        help="Comma-separated list of response codes to ignore"
    )
    group.add_argument(
        "-S", dest="showssl", action="store_true", default=False,
        help="Show info on SSL connection"
    )
    group.add_argument(
        "-e", dest="explain", action="store_true", default=False,
        help="Explain requests"
    )
    group.add_argument(
        "-o", dest="oneshot", action="store_true", default=False,
        help="Oneshot - exit after first non-ignored response"
    )
    group.add_argument(
        "-q", dest="showreq", action="store_true", default=False,
        help="Print full request"
    )
    group.add_argument(
        "-r", dest="showresp", action="store_true", default=False,
        help="Print full response"
    )
    group.add_argument(
        "-T", dest="ignoretimeout", action="store_true", default=False,
        help="Ignore timeouts"
    )
    group.add_argument(
        "-x", dest="hexdump", action="store_true", default=False,
        help="Output in hexdump format"
    )

    args = parser.parse_args()

    if args.port is None:
        args.port = 443 if args.ssl else 80
    else:
        args.port = args.port

    try:
        args.ignorecodes = [int(i) for i in args.ignorecodes.split(",") if i]
    except ValueError:
        parser.error("Invalid return code specification: %s"%args.ignorecodes)

    if args.connect_to:
        parts = args.connect_to.split(":")
        if len(parts) != 2:
            parser.error("Invalid CONNECT specification: %s"%args.connect_to)
        try:
            parts[1] = int(parts[1])
        except ValueError:
            parser.error("Invalid CONNECT specification: %s"%args.connect_to)
        args.connect_to = parts
    else:
        args.connect_to = None
    pathoc.main(args)


def go_pathod():
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
        help='Port. Specify 0 to pick an arbitrary empty port.'
    )
    parser.add_argument(
        "-l",
        dest='address',
        default="127.0.0.1",
        type=str,
        help='Listening address.'
    )
    parser.add_argument(
        "-a",
        dest='anchors',
        default=[],
        type=str,
        action="append",
        metavar="ANCHOR",
        help='Add an anchor. Specified as a string with the form pattern=pagespec'
    )
    parser.add_argument(
        "-c", dest='craftanchor', default="/p/", type=str,
        help='Anchorpoint for URL crafting commands.'
    )
    parser.add_argument(
        "--confdir",
        action="store", type = str, dest="confdir", default='~/.mitmproxy',
        help = "Configuration directory. (~/.mitmproxy)"
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
        "--limit-size", dest='sizelimit', default=None, type=str,
        help='Size limit of served responses. Understands size suffixes, i.e. 100k.'
    )
    parser.add_argument(
        "--noapi", dest='noapi', default=False, action="store_true",
        help='Disable API.'
    )
    parser.add_argument(
        "--nohang", dest='nohang', default=False, action="store_true",
        help='Disable pauses during crafted response generation.'
    )
    parser.add_argument(
        "--noweb", dest='noweb', default=False, action="store_true",
        help='Disable both web interface and API.'
    )
    parser.add_argument(
        "--nocraft", dest='nocraft', default=False, action="store_true",
        help='Disable response crafting. If anchors are specified, they still work.'
    )

    group = parser.add_argument_group(
        'SSL',
    )
    group.add_argument(
        "-s", dest='ssl', default=False, action="store_true",
        help='Run in HTTPS mode.'
    )
    group.add_argument(
        "--cn", dest="cn", type=str, default=None,
        help="CN for generated SSL certs. Default: %s"%pathod.DEFAULT_CERT_DOMAIN
    )
    group.add_argument(
        "-C", dest='ssl_not_after_connect', default=False, action="store_true",
        help="Don't expect SSL after a CONNECT request."
    )
    group.add_argument(
        "--cert", dest='ssl_certs', default=[], type=str,
        metavar = "SPEC", action="append",
        help = """
        Add an SSL certificate. SPEC is of the form "[domain=]path". The domain
        may include a wildcard, and is equal to "*" if not specified. The file
        at path is a certificate in PEM format. If a private key is included in
        the PEM, it is used, else the default key in the conf dir is used. Can
        be passed multiple times.'
        """
    )
    group.add_argument(
        "--ciphers", dest="ciphers", type=str, default=False,
        help="SSL cipher specification"
    )
    group.add_argument(
        "--sslversion", dest="sslversion", type=int, default=4,
        choices=[1, 2, 3, 4],
        help="Use a specified protocol - TLSv1, SSLv2, SSLv3, SSLv23. Default to SSLv23."
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
    args = parser.parse_args()

    certs = []
    for i in args.ssl_certs:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        parts[1] = os.path.expanduser(parts[1])
        if not os.path.exists(parts[1]):
            parser.error("Certificate file does not exist: %s"%parts[1])
        certs.append(parts)
    args.ssl_certs = certs

    alst = []
    for i in args.anchors:
        parts = utils.parse_anchor_spec(i)
        if not parts:
            parser.error("Invalid anchor specification: %s"%i)
        alst.append(parts)
    args.anchors = alst

    sizelimit = None
    if args.sizelimit:
        try:
            sizelimit = utils.parse_size(args.sizelimit)
        except ValueError, v:
            parser.error(v)
    args.sizelimit = sizelimit

    pathod.main(args)

