from __future__ import print_function
import sys
import argparse
import os
import os.path

from netlib import tcp
from netlib import version
from netlib.http import user_agents
from . import pathoc, language


def args_pathoc(argv, stdout=sys.stdout, stderr=sys.stderr):
    preparser = argparse.ArgumentParser(add_help=False)
    preparser.add_argument(
        "--show-uas", dest="showua", action="store_true", default=False,
        help="Print user agent shortcuts and exit."
    )
    pa = preparser.parse_known_args(argv)[0]
    if pa.showua:
        print("User agent strings:", file=stdout)
        for i in user_agents.UASTRINGS:
            print("  ", i[1], i[0], file=stdout)
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
        metavar="HOST:PORT",
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
            means requests have to be rendered in memory, which means that
            large generated data can cause issues.
        """
    )
    parser.add_argument(
        "-n", dest='repeat', default=1, type=int, metavar="N",
        help='Repeat N times. Pass -1 to repeat infinitely.'
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
        "--http2", dest="use_http2", action="store_true", default=False,
        help='Perform all requests over a single HTTP/2 connection.'
    )
    parser.add_argument(
        "--http2-skip-connection-preface",
        dest="http2_skip_connection_preface",
        action="store_true",
        default=False,
        help='Skips the HTTP/2 connection preface before sending requests.')

    parser.add_argument(
        'host', type=str,
        metavar="host[:port]",
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
        "--ssl-version", dest="ssl_version", type=str, default="secure",
        choices=tcp.sslversion_choices.keys(),
        help="Set supported SSL/TLS versions. "
             "SSLv2, SSLv3 and 'all' are INSECURE. Defaults to secure, which is TLS1.0+."
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
    group.add_argument(
        "--http2-framedump", dest="http2_framedump", action="store_true", default=False,
        help="Output all received & sent HTTP/2 frames"
    )

    args = parser.parse_args(argv[1:])

    args.ssl_version, args.ssl_options = tcp.sslversion_choices[args.ssl_version]

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
        return parser.error(
            "Invalid return code specification: %s" %
            args.ignorecodes)

    if args.connect_to:
        parts = args.connect_to.split(":")
        if len(parts) != 2:
            return parser.error(
                "Invalid CONNECT specification: %s" %
                args.connect_to)
        try:
            parts[1] = int(parts[1])
        except ValueError:
            return parser.error(
                "Invalid CONNECT specification: %s" %
                args.connect_to)
        args.connect_to = parts
    else:
        args.connect_to = None

    if args.http2_skip_connection_preface:
        args.use_http2 = True

    if args.use_http2:
        args.ssl = True

    reqs = []
    for r in args.requests:
        if os.path.isfile(r):
            with open(r) as f:
                r = f.read()
        try:
            reqs.append(language.parse_pathoc(r, args.use_http2))
        except language.ParseException as v:
            print("Error parsing request spec: %s" % v.msg, file=stderr)
            print(v.marked(), file=stderr)
            sys.exit(1)
    args.requests = reqs
    return args


def go_pathoc():  # pragma: no cover
    args = args_pathoc(sys.argv)
    pathoc.main(args)
