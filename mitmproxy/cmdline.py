from __future__ import absolute_import, print_function, division

import configargparse
import os
import re
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import options
from mitmproxy import platform
from netlib import human
from netlib import tcp
from netlib import version


class ParseException(Exception):
    pass


def _parse_hook(s):
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        patt = ".*"
        a, b = parts
    elif len(parts) == 3:
        patt, a, b = parts
    else:
        raise ParseException(
            "Malformed hook specifier - too few clauses: %s" % s
        )

    if not a:
        raise ParseException("Empty clause: %s" % str(patt))

    if not flowfilter.parse(patt):
        raise ParseException("Malformed filter pattern: %s" % patt)

    return patt, a, b


def parse_replace_hook(s):
    """
        Returns a (pattern, regex, replacement) tuple.

        The general form for a replacement hook is as follows:

            /patt/regex/replacement

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar/

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the replacement clause below is
        "foo/bar/":

            /one/two/foo/bar/

        Checks that pattern and regex are both well-formed. Raises
        ParseException on error.
    """
    patt, regex, replacement = _parse_hook(s)
    try:
        re.compile(regex)
    except re.error as e:
        raise ParseException("Malformed replacement regex: %s" % str(e))
    return patt, regex, replacement


def parse_setheader(s):
    """
        Returns a (pattern, header, value) tuple.

        The general form for a replacement hook is as follows:

            /patt/header/value

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar/

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the value clause below is
        "foo/bar/":

            /one/two/foo/bar/

        Checks that pattern and regex are both well-formed. Raises
        ParseException on error.
    """
    return _parse_hook(s)


def get_common_options(args):
    stickycookie, stickyauth = None, None
    if args.stickycookie_filt:
        stickycookie = args.stickycookie_filt

    if args.stickyauth_filt:
        stickyauth = args.stickyauth_filt

    stream_large_bodies = args.stream_large_bodies
    if stream_large_bodies:
        stream_large_bodies = human.parse_size(stream_large_bodies)

    reps = []
    for i in args.replace:
        try:
            p = parse_replace_hook(i)
        except ParseException as e:
            raise exceptions.OptionsError(e)
        reps.append(p)
    for i in args.replace_file:
        try:
            patt, rex, path = parse_replace_hook(i)
        except ParseException as e:
            raise exceptions.OptionsError(e)
        try:
            v = open(path, "rb").read()
        except IOError as e:
            raise exceptions.OptionsError(
                "Could not read replace file: %s" % path
            )
        reps.append((patt, rex, v))

    setheaders = []
    for i in args.setheader:
        try:
            p = parse_setheader(i)
        except ParseException as e:
            raise exceptions.OptionsError(e)
        setheaders.append(p)

    if args.outfile and args.outfile[0] == args.rfile:
        if args.outfile[1] == "wb":
            raise exceptions.OptionsError(
                "Cannot use '{}' for both reading and writing flows. "
                "Are you looking for --afile?".format(args.rfile)
            )
        else:
            raise exceptions.OptionsError(
                "Cannot use '{}' for both reading and appending flows. "
                "That would trigger an infinite loop."
            )

    # Proxy config
    certs = []
    for i in args.certs:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        certs.append(parts)

    body_size_limit = args.body_size_limit
    if body_size_limit:
        try:
            body_size_limit = human.parse_size(body_size_limit)
        except ValueError as e:
            raise exceptions.OptionsError(
                "Invalid body size limit specification: %s" % body_size_limit
            )

    # Establish proxy mode
    c = 0
    mode, upstream_server = "regular", None
    if args.transparent_proxy:
        c += 1
        if not platform.resolver:
            raise exceptions.OptionsError(
                "Transparent mode not supported on this platform."
            )
        mode = "transparent"
    if args.socks_proxy:
        c += 1
        mode = "socks5"
    if args.reverse_proxy:
        c += 1
        mode = "reverse"
        upstream_server = args.reverse_proxy
    if args.upstream_proxy:
        c += 1
        mode = "upstream"
        upstream_server = args.upstream_proxy
    if c > 1:
        raise exceptions.OptionsError(
            "Transparent, SOCKS5, reverse and upstream proxy mode "
            "are mutually exclusive. Read the docs on proxy modes "
            "to understand why."
        )
    if args.add_upstream_certs_to_client_chain and args.no_upstream_cert:
        raise exceptions.OptionsError(
            "The no-upstream-cert and add-upstream-certs-to-client-chain "
            "options are mutually exclusive. If no-upstream-cert is enabled "
            "then the upstream certificate is not retrieved before generating "
            "the client certificate chain."
        )

    if args.quiet:
        args.verbose = 0

    return dict(
        app=args.app,
        app_host=args.app_host,
        app_port=args.app_port,

        anticache=args.anticache,
        anticomp=args.anticomp,
        client_replay=args.client_replay,
        replay_kill_extra=args.replay_kill_extra,
        no_server=args.no_server,
        refresh_server_playback=not args.norefresh,
        server_replay_use_headers=args.server_replay_use_headers,
        rfile=args.rfile,
        replacements=reps,
        setheaders=setheaders,
        server_replay=args.server_replay,
        scripts=args.scripts,
        stickycookie=stickycookie,
        stickyauth=stickyauth,
        stream_large_bodies=stream_large_bodies,
        showhost=args.showhost,
        outfile=args.outfile,
        verbosity=args.verbose,
        server_replay_nopop=args.server_replay_nopop,
        server_replay_ignore_content=args.server_replay_ignore_content,
        server_replay_ignore_params=args.server_replay_ignore_params,
        server_replay_ignore_payload_params=args.server_replay_ignore_payload_params,
        server_replay_ignore_host=args.server_replay_ignore_host,

        auth_nonanonymous = args.auth_nonanonymous,
        auth_singleuser = args.auth_singleuser,
        auth_htpasswd = args.auth_htpasswd,
        add_upstream_certs_to_client_chain = args.add_upstream_certs_to_client_chain,
        body_size_limit = body_size_limit,
        cadir = args.cadir,
        certs = certs,
        ciphers_client = args.ciphers_client,
        ciphers_server = args.ciphers_server,
        clientcerts = args.clientcerts,
        http2 = args.http2,
        ignore_hosts = args.ignore_hosts,
        listen_host = args.addr,
        listen_port = args.port,
        mode = mode,
        no_upstream_cert = args.no_upstream_cert,
        spoof_source_address = args.spoof_source_address,
        rawtcp = args.rawtcp,
        websockets = args.websockets,
        upstream_server = upstream_server,
        upstream_auth = args.upstream_auth,
        ssl_version_client = args.ssl_version_client,
        ssl_version_server = args.ssl_version_server,
        ssl_insecure = args.ssl_insecure,
        ssl_verify_upstream_trusted_cadir = args.ssl_verify_upstream_trusted_cadir,
        ssl_verify_upstream_trusted_ca = args.ssl_verify_upstream_trusted_ca,
        tcp_hosts = args.tcp_hosts,
    )


def basic_options(parser):
    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s" + " " + version.VERSION
    )
    parser.add_argument(
        '--sysinfo',
        action='store_true',
        dest='sysinfo',
    )
    parser.add_argument(
        '--shortversion',
        action='version',
        help="show program's short version number and exit",
        version=version.VERSION
    )
    parser.add_argument(
        "--anticache",
        action="store_true", dest="anticache", default=False,

        help="""
            Strip out request headers that might cause the server to return
            304-not-modified.
        """
    )
    parser.add_argument(
        "--cadir",
        action="store", type=str, dest="cadir", default=options.CA_DIR,
        help="Location of the default mitmproxy CA files. (%s)" % options.CA_DIR
    )
    parser.add_argument(
        "--host",
        action="store_true", dest="showhost", default=False,
        help="Use the Host header to construct URLs for display."
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true", dest="quiet",
        help="Quiet."
    )
    parser.add_argument(
        "-r", "--read-flows",
        action="store", dest="rfile", default=None,
        help="Read flows from file."
    )
    parser.add_argument(
        "-s", "--script",
        action="append", type=str, dest="scripts", default=[],
        metavar='"script.py --bar"',
        help="""
            Run a script. Surround with quotes to pass script arguments. Can be
            passed multiple times.
        """
    )
    parser.add_argument(
        "-t", "--stickycookie",
        action="store",
        dest="stickycookie_filt",
        default=None,
        metavar="FILTER",
        help="Set sticky cookie filter. Matched against requests."
    )
    parser.add_argument(
        "-u", "--stickyauth",
        action="store", dest="stickyauth_filt", default=None, metavar="FILTER",
        help="Set sticky auth filter. Matched against requests."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_const", dest="verbose", default=2, const=3,
        help="Increase log verbosity."
    )
    outfile = parser.add_mutually_exclusive_group()
    outfile.add_argument(
        "-w", "--wfile",
        action="store", dest="outfile", type=lambda f: (f, "wb"),
        help="Write flows to file."
    )
    outfile.add_argument(
        "-a", "--afile",
        action="store", dest="outfile", type=lambda f: (f, "ab"),
        help="Append flows to file."
    )
    parser.add_argument(
        "-z", "--anticomp",
        action="store_true", dest="anticomp", default=False,
        help="Try to convince servers to send us un-compressed data."
    )
    parser.add_argument(
        "-Z", "--body-size-limit",
        action="store", dest="body_size_limit", default=None,
        metavar="SIZE",
        help="Byte size limit of HTTP request and response bodies."
             " Understands k/m/g suffixes, i.e. 3m for 3 megabytes."
    )
    parser.add_argument(
        "--stream",
        action="store", dest="stream_large_bodies", default=None,
        metavar="SIZE",
        help="""
            Stream data to the client if response body exceeds the given
            threshold. If streamed, the body will not be stored in any way.
            Understands k/m/g suffixes, i.e. 3m for 3 megabytes.
         """
    )


def proxy_modes(parser):
    group = parser.add_argument_group("Proxy Modes")
    group.add_argument(
        "-R", "--reverse",
        action="store",
        type=str,
        dest="reverse_proxy",
        default=None,
        help="""
            Forward all requests to upstream HTTP server:
            http[s]://host[:port]. Clients can always connect both
            via HTTPS and HTTP, the connection to the server is
            determined by the specified scheme.
        """
    )
    group.add_argument(
        "--socks",
        action="store_true", dest="socks_proxy", default=False,
        help="Set SOCKS5 proxy mode."
    )
    group.add_argument(
        "-T", "--transparent",
        action="store_true", dest="transparent_proxy", default=False,
        help="Set transparent proxy mode."
    )
    group.add_argument(
        "-U", "--upstream",
        action="store",
        type=str,
        dest="upstream_proxy",
        default=None,
        help="Forward all requests to upstream proxy server: http://host[:port]"
    )


def proxy_options(parser):
    group = parser.add_argument_group("Proxy Options")
    group.add_argument(
        "-b", "--bind-address",
        action="store", type=str, dest="addr", default='',
        help="Address to bind proxy to (defaults to all interfaces)"
    )
    group.add_argument(
        "-I", "--ignore",
        action="append", type=str, dest="ignore_hosts", default=[],
        metavar="HOST",
        help="""
            Ignore host and forward all traffic without processing it. In
            transparent mode, it is recommended to use an IP address (range),
            not the hostname. In regular mode, only SSL traffic is ignored and
            the hostname should be used. The supplied value is interpreted as a
            regular expression and matched on the ip or the hostname. Can be
            passed multiple times.
        """
    )
    group.add_argument(
        "--tcp",
        action="append", type=str, dest="tcp_hosts", default=[],
        metavar="HOST",
        help="""
            Generic TCP SSL proxy mode for all hosts that match the pattern.
            Similar to --ignore, but SSL connections are intercepted. The
            communication contents are printed to the log in verbose mode.
        """
    )
    group.add_argument(
        "-n", "--no-server",
        action="store_true", dest="no_server",
        help="Don't start a proxy server."
    )
    group.add_argument(
        "-p", "--port",
        action="store", type=int, dest="port", default=options.LISTEN_PORT,
        help="Proxy service port."
    )
    group.add_argument(
        "--no-http2",
        action="store_false", dest="http2",
        help="""
            Explicitly disable HTTP/2 support.
            If your OpenSSL version supports ALPN, HTTP/2 is enabled by default.
        """
    )
    parser.add_argument(
        "--upstream-auth",
        action="store", dest="upstream_auth", default=None,
        type=str,
        help="""
            Proxy Authentication:
            username:password
        """
    )
    rawtcp = group.add_mutually_exclusive_group()
    rawtcp.add_argument("--raw-tcp", action="store_true", dest="rawtcp")
    rawtcp.add_argument("--no-raw-tcp", action="store_false", dest="rawtcp",
                        help="Explicitly enable/disable experimental raw tcp support. "
                        "Disabled by default. "
                        "Default value will change in a future version."
                        )
    websockets = group.add_mutually_exclusive_group()
    websockets.add_argument("--websockets", action="store_true", dest="websockets")
    websockets.add_argument("--no-websockets", action="store_false", dest="websockets",
                            help="Explicitly enable/disable experimental WebSocket support. "
                                 "Disabled by default as messages are only printed to the event log and not retained. "
                                 "Default value will change in a future version."
                            )
    group.add_argument(
        "--spoof-source-address",
        action="store_true", dest="spoof_source_address",
        help="Use the client's IP for server-side connections"
    )


def proxy_ssl_options(parser):
    # TODO: Agree to consistently either use "upstream" or "server".
    group = parser.add_argument_group("SSL")
    group.add_argument(
        "--cert",
        dest='certs',
        default=[],
        type=str,
        metavar="SPEC",
        action="append",
        help='Add an SSL certificate. SPEC is of the form "[domain=]path". '
             'The domain may include a wildcard, and is equal to "*" if not specified. '
             'The file at path is a certificate in PEM format. If a private key is included '
             'in the PEM, it is used, else the default key in the conf dir is used. '
             'The PEM file should contain the full certificate chain, with the leaf certificate '
             'as the first entry. Can be passed multiple times.')
    group.add_argument(
        "--ciphers-client", action="store",
        type=str, dest="ciphers_client", default=options.DEFAULT_CLIENT_CIPHERS,
        help="Set supported ciphers for client connections. (OpenSSL Syntax)"
    )
    group.add_argument(
        "--ciphers-server", action="store",
        type=str, dest="ciphers_server", default=None,
        help="Set supported ciphers for server connections. (OpenSSL Syntax)"
    )
    group.add_argument(
        "--client-certs", action="store",
        type=str, dest="clientcerts", default=None,
        help="Client certificate file or directory."
    )
    group.add_argument(
        "--no-upstream-cert", default=False,
        action="store_true", dest="no_upstream_cert",
        help="Don't connect to upstream server to look up certificate details."
    )
    group.add_argument(
        "--add-upstream-certs-to-client-chain", default=False,
        action="store_true", dest="add_upstream_certs_to_client_chain",
        help="Add all certificates of the upstream server to the certificate chain "
             "that will be served to the proxy client, as extras."
    )
    group.add_argument(
        "--insecure", default=False,
        action="store_true", dest="ssl_insecure",
        help="Do not verify upstream server SSL/TLS certificates."
    )
    group.add_argument(
        "--upstream-trusted-cadir", default=None, action="store",
        dest="ssl_verify_upstream_trusted_cadir",
        help="Path to a directory of trusted CA certificates for upstream "
             "server verification prepared using the c_rehash tool."
    )
    group.add_argument(
        "--upstream-trusted-ca", default=None, action="store",
        dest="ssl_verify_upstream_trusted_ca",
        help="Path to a PEM formatted trusted CA certificate."
    )
    group.add_argument(
        "--ssl-version-client", dest="ssl_version_client",
        default="secure", action="store",
        choices=tcp.sslversion_choices.keys(),
        help="Set supported SSL/TLS versions for client connections. "
             "SSLv2, SSLv3 and 'all' are INSECURE. Defaults to secure, which is TLS1.0+."
    )
    group.add_argument(
        "--ssl-version-server", dest="ssl_version_server",
        default="secure", action="store",
        choices=tcp.sslversion_choices.keys(),
        help="Set supported SSL/TLS versions for server connections. "
             "SSLv2, SSLv3 and 'all' are INSECURE. Defaults to secure, which is TLS1.0+."
    )


def onboarding_app(parser):
    group = parser.add_argument_group("Onboarding App")
    group.add_argument(
        "--noapp",
        action="store_false", dest="app", default=True,
        help="Disable the mitmproxy onboarding app."
    )
    group.add_argument(
        "--app-host",
        action="store", dest="app_host", default=options.APP_HOST, metavar="host",
        help="""
            Domain to serve the onboarding app from. For transparent mode, use
            an IP when a DNS entry for the app domain is not present. Default:
            %s
        """ % options.APP_HOST
    )
    group.add_argument(
        "--app-port",
        action="store",
        dest="app_port",
        default=options.APP_PORT,
        type=int,
        metavar="80",
        help="Port to serve the onboarding app from."
    )


def client_replay(parser):
    group = parser.add_argument_group("Client Replay")
    group.add_argument(
        "-c", "--client-replay",
        action="append", dest="client_replay", default=None, metavar="PATH",
        help="Replay client requests from a saved file."
    )


def server_replay(parser):
    group = parser.add_argument_group("Server Replay")
    group.add_argument(
        "-S", "--server-replay",
        action="append", dest="server_replay", default=None, metavar="PATH",
        help="Replay server responses from a saved file."
    )
    group.add_argument(
        "-k", "--replay-kill-extra",
        action="store_true", dest="replay_kill_extra", default=False,
        help="Kill extra requests during replay."
    )
    group.add_argument(
        "--server-replay-use-header",
        action="append", dest="server_replay_use_headers", type=str,
        help="Request headers to be considered during replay. "
             "Can be passed multiple times."
    )
    group.add_argument(
        "--norefresh",
        action="store_true", dest="norefresh", default=False,
        help="""
            Disable response refresh, which updates times in cookies and headers
            for replayed responses.
        """
    )
    group.add_argument(
        "--no-pop",
        action="store_true", dest="server_replay_nopop", default=False,
        help="Disable response pop from response flow. "
             "This makes it possible to replay same response multiple times."
    )
    payload = group.add_mutually_exclusive_group()
    payload.add_argument(
        "--replay-ignore-content",
        action="store_true", dest="server_replay_ignore_content", default=False,
        help="""
            Ignore request's content while searching for a saved flow to replay
        """
    )
    payload.add_argument(
        "--replay-ignore-payload-param",
        action="append", dest="server_replay_ignore_payload_params", type=str,
        help="""
            Request's payload parameters (application/x-www-form-urlencoded or multipart/form-data) to
            be ignored while searching for a saved flow to replay.
            Can be passed multiple times.
        """
    )

    group.add_argument(
        "--replay-ignore-param",
        action="append", dest="server_replay_ignore_params", type=str,
        help="""
            Request's parameters to be ignored while searching for a saved flow
            to replay. Can be passed multiple times.
        """
    )
    group.add_argument(
        "--replay-ignore-host",
        action="store_true",
        dest="server_replay_ignore_host",
        default=False,
        help="Ignore request's destination host while searching for a saved flow to replay")


def replacements(parser):
    group = parser.add_argument_group(
        "Replacements",
        """
            Replacements are of the form "/pattern/regex/replacement", where
            the separator can be any character. Please see the documentation
            for more information.
        """.strip()
    )
    group.add_argument(
        "--replace",
        action="append", type=str, dest="replace", default=[],
        metavar="PATTERN",
        help="Replacement pattern."
    )
    group.add_argument(
        "--replace-from-file",
        action="append", type=str, dest="replace_file", default=[],
        metavar="PATH",
        help="""
            Replacement pattern, where the replacement clause is a path to a
            file.
        """
    )


def set_headers(parser):
    group = parser.add_argument_group(
        "Set Headers",
        """
            Header specifications are of the form "/pattern/header/value",
            where the separator can be any character. Please see the
            documentation for more information.
        """.strip()
    )
    group.add_argument(
        "--setheader",
        action="append", type=str, dest="setheader", default=[],
        metavar="PATTERN",
        help="Header set pattern."
    )


def proxy_authentication(parser):
    group = parser.add_argument_group(
        "Proxy Authentication",
        """
            Specify which users are allowed to access the proxy and the method
            used for authenticating them.
        """
    ).add_mutually_exclusive_group()
    group.add_argument(
        "--nonanonymous",
        action="store_true", dest="auth_nonanonymous",
        help="Allow access to any user long as a credentials are specified."
    )

    group.add_argument(
        "--singleuser",
        action="store", dest="auth_singleuser", type=str,
        metavar="USER",
        help="""
            Allows access to a a single user, specified in the form
            username:password.
        """
    )
    group.add_argument(
        "--htpasswd",
        action="store", dest="auth_htpasswd", type=str,
        metavar="PATH",
        help="Allow access to users specified in an Apache htpasswd file."
    )


def common_options(parser):
    basic_options(parser)
    proxy_modes(parser)
    proxy_options(parser)
    proxy_ssl_options(parser)
    onboarding_app(parser)
    client_replay(parser)
    server_replay(parser)
    replacements(parser)
    set_headers(parser)
    proxy_authentication(parser)


def mitmproxy():
    # Don't import mitmproxy.console for mitmdump, urwid is not available on all
    # platforms.
    from .console import palettes

    parser = configargparse.ArgumentParser(
        usage="%(prog)s [options]",
        args_for_setting_config_path=["--conf"],
        default_config_files=[
            os.path.join(options.CA_DIR, "common.conf"),
            os.path.join(options.CA_DIR, "mitmproxy.conf")
        ],
        add_config_file_help=True,
        add_env_var_help=True
    )
    common_options(parser)
    parser.add_argument(
        "--palette", type=str, default=palettes.DEFAULT,
        action="store", dest="palette",
        choices=sorted(palettes.palettes.keys()),
        help="Select color palette: " + ", ".join(palettes.palettes.keys())
    )
    parser.add_argument(
        "--palette-transparent",
        action="store_true", dest="palette_transparent", default=False,
        help="Set transparent background for palette."
    )
    parser.add_argument(
        "-e", "--eventlog",
        action="store_true", dest="eventlog",
        help="Show event log."
    )
    parser.add_argument(
        "--follow",
        action="store_true", dest="follow",
        help="Follow flow list."
    )
    parser.add_argument(
        "--no-mouse",
        action="store_true", dest="no_mouse",
        help="Disable mouse interaction."
    )
    group = parser.add_argument_group(
        "Filters",
        "See help in mitmproxy for filter expression syntax."
    )
    group.add_argument(
        "-i", "--intercept", action="store",
        type=str, dest="intercept", default=None,
        help="Intercept filter expression."
    )
    group.add_argument(
        "-f", "--filter", action="store",
        type=str, dest="filter", default=None,
        help="Filter view expression."
    )
    return parser


def mitmdump():
    parser = configargparse.ArgumentParser(
        usage="%(prog)s [options] [filter]",
        args_for_setting_config_path=["--conf"],
        default_config_files=[
            os.path.join(options.CA_DIR, "common.conf"),
            os.path.join(options.CA_DIR, "mitmdump.conf")
        ],
        add_config_file_help=True,
        add_env_var_help=True
    )

    common_options(parser)
    parser.add_argument(
        "--keepserving",
        action="store_true", dest="keepserving", default=False,
        help="""
            Continue serving after client playback or file read. We exit by
            default.
        """
    )
    parser.add_argument(
        "-d", "--detail",
        action="count", dest="flow_detail", default=1,
        help="Increase flow detail display level. Can be passed multiple times."
    )
    parser.add_argument('args', nargs="...")
    return parser


def mitmweb():
    parser = configargparse.ArgumentParser(
        usage="%(prog)s [options]",
        args_for_setting_config_path=["--conf"],
        default_config_files=[
            os.path.join(options.CA_DIR, "common.conf"),
            os.path.join(options.CA_DIR, "mitmweb.conf")
        ],
        add_config_file_help=True,
        add_env_var_help=True
    )

    group = parser.add_argument_group("Mitmweb")
    group.add_argument(
        "--wport",
        action="store", type=int, dest="wport", default=8081,
        metavar="PORT",
        help="Mitmweb port."
    )
    group.add_argument(
        "--wiface",
        action="store", dest="wiface", default="127.0.0.1",
        metavar="IFACE",
        help="Mitmweb interface."
    )
    group.add_argument(
        "--wdebug",
        action="store_true", dest="wdebug",
        help="Turn on mitmweb debugging"
    )
    group.add_argument(
        "--wsingleuser",
        action="store", dest="wsingleuser", type=str,
        metavar="USER",
        help="""
            Allows access to a a single user, specified in the form
            username:password.
        """
    )
    group.add_argument(
        "--whtpasswd",
        action="store", dest="whtpasswd", type=str,
        metavar="PATH",
        help="Allow access to users specified in an Apache htpasswd file."
    )

    common_options(parser)
    group = parser.add_argument_group(
        "Filters",
        "See help in mitmproxy for filter expression syntax."
    )
    group.add_argument(
        "-i", "--intercept", action="store",
        type=str, dest="intercept", default=None,
        help="Intercept filter expression."
    )
    return parser
