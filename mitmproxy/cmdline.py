from __future__ import absolute_import
import os
import re
import base64

import configargparse

from netlib.tcp import Address, sslversion_choices
import netlib.utils
from . import filt, utils, version
from .proxy import config

APP_HOST = "mitm.it"
APP_PORT = 80


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

    if not filt.parse(patt):
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
        raise ParseException("Malformed replacement regex: %s" % str(e.message))
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


def parse_server_spec(url):
    try:
        p = netlib.utils.parse_url(url)
        if p[0] not in ("http", "https"):
            raise ValueError()
    except ValueError:
        raise configargparse.ArgumentTypeError(
            "Invalid server specification: %s" % url
        )

    address = Address(p[1:3])
    scheme = p[0].lower()
    return config.ServerSpec(scheme, address)


def parse_upstream_auth(auth):
    pattern = re.compile(".+:")
    if pattern.search(auth) is None:
        raise configargparse.ArgumentTypeError(
            "Invalid upstream auth specification: %s" % auth
        )
    return "Basic" + " " + base64.b64encode(auth)


def get_common_options(options):
    stickycookie, stickyauth = None, None
    if options.stickycookie_filt:
        stickycookie = options.stickycookie_filt

    if options.stickyauth_filt:
        stickyauth = options.stickyauth_filt

    stream_large_bodies = utils.parse_size(options.stream_large_bodies)

    reps = []
    for i in options.replace:
        try:
            p = parse_replace_hook(i)
        except ParseException as e:
            raise configargparse.ArgumentTypeError(e.message)
        reps.append(p)
    for i in options.replace_file:
        try:
            patt, rex, path = parse_replace_hook(i)
        except ParseException as e:
            raise configargparse.ArgumentTypeError(e.message)
        try:
            v = open(path, "rb").read()
        except IOError as e:
            raise configargparse.ArgumentTypeError(
                "Could not read replace file: %s" % path
            )
        reps.append((patt, rex, v))

    setheaders = []
    for i in options.setheader:
        try:
            p = parse_setheader(i)
        except ParseException as e:
            raise configargparse.ArgumentTypeError(e.message)
        setheaders.append(p)

    return dict(
        app=options.app,
        app_host=options.app_host,
        app_port=options.app_port,

        anticache=options.anticache,
        anticomp=options.anticomp,
        client_replay=options.client_replay,
        kill=options.kill,
        no_server=options.no_server,
        refresh_server_playback=not options.norefresh,
        rheaders=options.rheaders,
        rfile=options.rfile,
        replacements=reps,
        setheaders=setheaders,
        server_replay=options.server_replay,
        scripts=options.scripts,
        stickycookie=stickycookie,
        stickyauth=stickyauth,
        stream_large_bodies=stream_large_bodies,
        showhost=options.showhost,
        outfile=options.outfile,
        verbosity=options.verbose,
        nopop=options.nopop,
        replay_ignore_content=options.replay_ignore_content,
        replay_ignore_params=options.replay_ignore_params,
        replay_ignore_payload_params=options.replay_ignore_payload_params,
        replay_ignore_host=options.replay_ignore_host
    )


def basic_options(parser):
    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s" + " " + version.VERSION
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
        action="store", type=str, dest="cadir", default=config.CA_DIR,
        help="Location of the default mitmproxy CA files. (%s)" % config.CA_DIR
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
        action="store_const", dest="verbose", default=1, const=2,
        help="Increase event log verbosity."
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
    group = parser.add_argument_group("Proxy Modes").add_mutually_exclusive_group()
    group.add_argument(
        "-R", "--reverse",
        action="store",
        type=parse_server_spec,
        dest="reverse_proxy",
        default=None,
        help="""
            Forward all requests to upstream HTTP server:
            http[s][2http[s]]://host[:port]
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
        type=parse_server_spec,
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
            communication contents are printed to the event log in verbose mode.
        """
    )
    group.add_argument(
        "-n", "--no-server",
        action="store_true", dest="no_server",
        help="Don't start a proxy server."
    )
    group.add_argument(
        "-p", "--port",
        action="store", type=int, dest="port", default=8080,
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
        type=parse_upstream_auth,
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
        type=str, dest="ciphers_client", default=config.DEFAULT_CLIENT_CIPHERS,
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
        "--verify-upstream-cert", default=False,
        action="store_true", dest="ssl_verify_upstream_cert",
        help="Verify upstream server SSL/TLS certificates and fail if invalid "
             "or not present."
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
        choices=sslversion_choices.keys(),
        help="Set supported SSL/TLS versions for client connections. "
             "SSLv2, SSLv3 and 'all' are INSECURE. Defaults to secure, which is TLS1.0+."
    )
    group.add_argument(
        "--ssl-version-server", dest="ssl_version_server",
        default="secure", action="store",
        choices=sslversion_choices.keys(),
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
        action="store", dest="app_host", default=APP_HOST, metavar="host",
        help="""
            Domain to serve the onboarding app from. For transparent mode, use
            an IP when a DNS entry for the app domain is not present. Default:
            %s
        """ % APP_HOST
    )
    group.add_argument(
        "--app-port",
        action="store",
        dest="app_port",
        default=APP_PORT,
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
        "-k", "--kill",
        action="store_true", dest="kill", default=False,
        help="Kill extra requests during replay."
    )
    group.add_argument(
        "--rheader",
        action="append", dest="rheaders", type=str,
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
        action="store_true", dest="nopop", default=False,
        help="Disable response pop from response flow. "
             "This makes it possible to replay same response multiple times."
    )
    payload = group.add_mutually_exclusive_group()
    payload.add_argument(
        "--replay-ignore-content",
        action="store_true", dest="replay_ignore_content", default=False,
        help="""
            Ignore request's content while searching for a saved flow to replay
        """
    )
    payload.add_argument(
        "--replay-ignore-payload-param",
        action="append", dest="replay_ignore_payload_params", type=str,
        help="""
            Request's payload parameters (application/x-www-form-urlencoded or multipart/form-data) to
            be ignored while searching for a saved flow to replay.
            Can be passed multiple times.
        """
    )

    group.add_argument(
        "--replay-ignore-param",
        action="append", dest="replay_ignore_params", type=str,
        help="""
            Request's parameters to be ignored while searching for a saved flow
            to replay. Can be passed multiple times.
        """
    )
    group.add_argument(
        "--replay-ignore-host",
        action="store_true",
        dest="replay_ignore_host",
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
            os.path.join(config.CA_DIR, "common.conf"),
            os.path.join(config.CA_DIR, "mitmproxy.conf")
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
        "-f", "--follow",
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
        "-l", "--limit", action="store",
        type=str, dest="limit", default=None,
        help="Limit filter expression."
    )
    return parser


def mitmdump():
    parser = configargparse.ArgumentParser(
        usage="%(prog)s [options] [filter]",
        args_for_setting_config_path=["--conf"],
        default_config_files=[
            os.path.join(config.CA_DIR, "common.conf"),
            os.path.join(config.CA_DIR, "mitmdump.conf")
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
            os.path.join(config.CA_DIR, "common.conf"),
            os.path.join(config.CA_DIR, "mitmweb.conf")
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
