#!/usr/bin/env python
import argparse
import os
import os.path
import sys
import re
from . import pathoc, pathod, version, utils, language
from netlib import http_uastrings


def args_pathoc(argv, stdout=sys.stdout, stderr=sys.stderr):
    preparser = argparse.ArgumentParser(add_help=False)
    preparser.add_argument(
        "--show-uas", dest="showua", action="store_true", default=False,
        help="Print user agent shortcuts and exit."
    )
    pa = preparser.parse_known_args(argv)[0]
    if pa.showua:
        print >> stdout, "User agent strings:"
        for i in http_uastrings.UASTRINGS:
            print >> stdout, "  ", i[1], i[0]
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
        "--memo-limit", dest='memolimit', default=5000, type=int, metavar="N",
        help='Stop if we do not find a valid request after N attempts.'
    )
    parser.add_argument(
        "-m", dest='memo', action="store_true", default=False,
        help="""
            Remember specs, and never play the same one twice. Note that this
            means requests have to be rendered in memory, which means that large
            generated data can cause issues.
        """
    )
    parser.add_argument(
        "-n", dest='repeat', default=1, type=int, metavar="N",
        help='Repeat N times. If 0 repeat for ever.'
    )
    parser.add_argument(
        "-w", dest='wait', default=0, type=float, metavar="N",
        help='Wait N seconds between each request.'
    )
    parser.add_argument(
        "-r", dest="random", action="store_true", default=False,
        help="""
        Select a random request from those specified. If this is not specified,
        requests are all played in sequence.
        """
    )
    parser.add_argument(
        "-t", dest="timeout", type=int, default=None,
        help="Connection timeout"
    )
    parser.add_argument(
        'host', type=str,
        metavar = "host[:port]",
        help='Host and port to connect to'
    )
    parser.add_argument(
        'requests', type=str, nargs="+",
        help="""
        Request specification, or path to a file containing request
        specifcations
        """
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
        help="""
            Use a specified protocol - TLSv1, SSLv2, SSLv3, SSLv23. Default
            to SSLv23.
        """
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
        "-p", dest="showresp", action="store_true", default=False,
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

    args = parser.parse_args(argv[1:])

    args.port = None
    if ":" in args.host:
        h, p = args.host.rsplit(":", 1)
        try:
            p = int(p)
        except ValueError:
            return parser.error("Invalid port in host spec: %s" % args.host)
        args.host = h
        args.port = p

    if args.port is None:
        args.port = 443 if args.ssl else 80

    try:
        args.ignorecodes = [int(i) for i in args.ignorecodes.split(",") if i]
    except ValueError:
        return parser.error("Invalid return code specification: %s"%args.ignorecodes)

    if args.connect_to:
        parts = args.connect_to.split(":")
        if len(parts) != 2:
            return parser.error("Invalid CONNECT specification: %s"%args.connect_to)
        try:
            parts[1] = int(parts[1])
        except ValueError:
            return parser.error("Invalid CONNECT specification: %s"%args.connect_to)
        args.connect_to = parts
    else:
        args.connect_to = None

    reqs = []
    for r in args.requests:
        if os.path.isfile(r):
            data = open(r).read()
            r = data
        try:
            reqs.extend(language.parse_requests(r))
        except language.ParseException, v:
            print >> stderr, "Error parsing request spec: %s"%v.msg
            print >> stderr, v.marked()
            sys.exit(1)
    args.requests = reqs
    return args


def go_pathoc(): #  pragma: nocover
    args = args_pathoc(sys.argv)
    pathoc.main(args)


def args_pathod(argv, stdout=sys.stdout, stderr=sys.stderr):
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
        help="""
        Add an anchor. Specified as a string with the form pattern=pagespec, or
        pattern=filepath
        """
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
        be passed multiple times.
        """
    )
    group.add_argument(
        "--ciphers", dest="ciphers", type=str, default=False,
        help="SSL cipher specification"
    )
    group.add_argument(
        "--sans", dest="sans", type=str, default="",
        help="""Comma-separated list of subject Altnernate Names to add to
        the server certificate."""
    )
    group.add_argument(
        "--sslversion", dest="sslversion", type=int, default=4,
        choices=[1, 2, 3, 4],
        help=""""Use a specified protocol - TLSv1, SSLv2, SSLv3, SSLv23. Default
        to SSLv23."""
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
    args = parser.parse_args(argv[1:])

    args.sans = args.sans.split(",")

    certs = []
    for i in args.ssl_certs:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        parts[1] = os.path.expanduser(parts[1])
        if not os.path.isfile(parts[1]):
            return parser.error("Certificate file does not exist: %s"%parts[1])
        certs.append(parts)
    args.ssl_certs = certs

    alst = []
    for i in args.anchors:
        parts = utils.parse_anchor_spec(i)
        if not parts:
            return parser.error("Invalid anchor specification: %s"%i)
        alst.append(parts)
    args.anchors = alst

    sizelimit = None
    if args.sizelimit:
        try:
            sizelimit = utils.parse_size(args.sizelimit)
        except ValueError, v:
            return parser.error(v)
    args.sizelimit = sizelimit

    anchors = []
    for patt, spec in args.anchors:
        if os.path.isfile(spec):
            data = open(spec).read()
            spec = data

        try:
            req = language.parse_response(spec)
        except language.ParseException, v:
            print >> stderr, "Error parsing anchor spec: %s"%v.msg
            print >> stderr, v.marked()
            sys.exit(1)
        try:
            arex = re.compile(patt)
        except re.error:
            return parser.error("Invalid regex in anchor: %s" % patt)
        anchors.append((arex, req))
    args.anchors = anchors
    return args


def go_pathod(): # pragma: nocover
    args = args_pathod(sys.argv)
    pathod.main(args)
