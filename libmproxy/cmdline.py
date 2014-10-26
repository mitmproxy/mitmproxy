from __future__ import absolute_import
import re
from argparse import ArgumentTypeError
from netlib import http
from . import filt, utils
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
        raise ParseException("Malformed hook specifier - too few clauses: %s" % s)

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
    except re.error, e:
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
    normalized_url = re.sub("^https?2", "", url)

    p = http.parse_url(normalized_url)
    if not p or not p[1]:
        raise ArgumentTypeError("Invalid server specification: %s" % url)

    if url.lower().startswith("https2http"):
        ssl = [True, False]
    elif url.lower().startswith("http2https"):
        ssl = [False, True]
    elif url.lower().startswith("https"):
        ssl = [True, True]
    else:
        ssl = [False, False]

    return ssl + list(p[1:3])


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
        except ParseException, e:
            raise ArgumentTypeError(e.message)
        reps.append(p)
    for i in options.replace_file:
        try:
            patt, rex, path = parse_replace_hook(i)
        except ParseException, e:
            raise ArgumentTypeError(e.message)
        try:
            v = open(path, "rb").read()
        except IOError, e:
            raise ArgumentTypeError("Could not read replace file: %s" % path)
        reps.append((patt, rex, v))

    setheaders = []
    for i in options.setheader:
        try:
            p = parse_setheader(i)
        except ParseException, e:
            raise ArgumentTypeError(e.message)
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
        wfile=options.wfile,
        verbosity=options.verbose,
        nopop=options.nopop,
        replay_ignore_content = options.replay_ignore_content,
        replay_ignore_params = options.replay_ignore_params
    )


def common_options(parser):
    parser.add_argument(
        "--anticache",
        action="store_true", dest="anticache", default=False,
        help="Strip out request headers that might cause the server to return 304-not-modified."
    )
    parser.add_argument(
        "--confdir",
        action="store", type=str, dest="confdir", default='~/.mitmproxy',
        help="Configuration directory, contains default CA file. (~/.mitmproxy)"
    )
    parser.add_argument(
        "--host",
        action="store_true", dest="showhost", default=False,
        help="Use the Host header to construct URLs for display."
    )
    parser.add_argument(
        "-q",
        action="store_true", dest="quiet",
        help="Quiet."
    )
    parser.add_argument(
        "-r",
        action="store", dest="rfile", default=None,
        help="Read flows from file."
    )
    parser.add_argument(
        "-s",
        action="append", type=str, dest="scripts", default=[],
        metavar='"script.py --bar"',
        help="Run a script. Surround with quotes to pass script arguments. Can be passed multiple times."
    )
    parser.add_argument(
        "-t",
        action="store", dest="stickycookie_filt", default=None, metavar="FILTER",
        help="Set sticky cookie filter. Matched against requests."
    )
    parser.add_argument(
        "-u",
        action="store", dest="stickyauth_filt", default=None, metavar="FILTER",
        help="Set sticky auth filter. Matched against requests."
    )
    parser.add_argument(
        "-v",
        action="store_const", dest="verbose", default=1, const=2,
        help="Increase event log verbosity."
    )
    parser.add_argument(
        "-w",
        action="store", dest="wfile", default=None,
        help="Write flows to file."
    )
    parser.add_argument(
        "-z",
        action="store_true", dest="anticomp", default=False,
        help="Try to convince servers to send us un-compressed data."
    )
    parser.add_argument(
        "-Z",
        action="store", dest="body_size_limit", default=None,
        metavar="SIZE",
        help="Byte size limit of HTTP request and response bodies." \
             " Understands k/m/g suffixes, i.e. 3m for 3 megabytes."
    )
    parser.add_argument(
        "--stream",
        action="store", dest="stream_large_bodies", default=None,
        metavar="SIZE",
        help="""
        Stream data to the client if response body exceeds the given threshold.
        If streamed, the body will not be stored in any way. Understands k/m/g
        suffixes, i.e. 3m for 3 megabytes.
         """
    )

    group = parser.add_argument_group("Proxy Options")
    # We could make a mutually exclusive group out of -R, -U, -T, but we don't
    # do that because  - --upstream-server should be in that group as well, but
    # it's already in a different group.  - our own error messages are more
    # helpful
    group.add_argument(
        "-b",
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
        help="Generic TCP SSL proxy mode for all hosts that match the pattern. Similar to --ignore,"
             "but SSL connections are intercepted. The communication contents are printed to the event log in verbose mode."
    )
    group.add_argument(
        "-n",
        action="store_true", dest="no_server",
        help="Don't start a proxy server."
    )
    group.add_argument(
        "-p",
        action="store", type=int, dest="port", default=8080,
        help="Proxy service port."
    )
    group.add_argument(
        "-R",
        action="store", type=parse_server_spec, dest="reverse_proxy", default=None,
        help="Forward all requests to upstream HTTP server: http[s][2http[s]]://host[:port]"
    )
    group.add_argument(
        "--socks",
        action="store_true", dest="socks_proxy", default=False,
        help="Set SOCKS5 proxy mode."
    )
    group.add_argument(
        "-T",
        action="store_true", dest="transparent_proxy", default=False,
        help="Set transparent proxy mode."
    )
    group.add_argument(
        "-U",
        action="store", type=parse_server_spec, dest="upstream_proxy", default=None,
        help="Forward all requests to upstream proxy server: http://host[:port]"
    )

    group = parser.add_argument_group(
        "Advanced Proxy Options",
        """
            The following options allow a custom adjustment of the proxy behavior.
            Normally, you don't want to use these options directly and use the provided wrappers instead (-R, -U, -T).
        """.strip()
    )
    group.add_argument(
        "--http-form-in", dest="http_form_in", default=None,
        action="store", choices=("relative", "absolute"),
        help="Override the HTTP request form accepted by the proxy"
    )
    group.add_argument(
        "--http-form-out", dest="http_form_out", default=None,
        action="store", choices=("relative", "absolute"),
        help="Override the HTTP request form sent upstream by the proxy"
    )

    group = parser.add_argument_group("Onboarding App")
    group.add_argument(
        "-a",
        action="store_false", dest="app", default=True,
        help="Disable the mitmproxy onboarding app."
    )
    group.add_argument(
        "--app-host",
        action="store", dest="app_host", default=APP_HOST, metavar="host",
        help="Domain to serve the onboarding app from. For transparent mode, use an IP when\
                a DNS entry for the app domain is not present. Default: %s" % APP_HOST

    )
    group.add_argument(
        "--app-port",
        action="store", dest="app_port", default=APP_PORT, type=int, metavar="80",
        help="Port to serve the onboarding app from."
    )

    group = parser.add_argument_group("Client Replay")
    group.add_argument(
        "-c",
        action="store", dest="client_replay", default=None, metavar="PATH",
        help="Replay client requests from a saved file."
    )

    group = parser.add_argument_group("Server Replay")
    group.add_argument(
        "-S",
        action="store", dest="server_replay", default=None, metavar="PATH",
        help="Replay server responses from a saved file."
    )
    group.add_argument(
        "-k",
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
        help="Disable response refresh, "
             "which updates times in cookies and headers for replayed responses."
    )
    group.add_argument(
        "--no-pop",
        action="store_true", dest="nopop", default=False,
        help="Disable response pop from response flow. "
             "This makes it possible to replay same response multiple times."
    )
    group.add_argument(
        "--replay-ignore-content",
        action="store_true", dest="replay_ignore_content", default=False,
        help="Ignore request's content while searching for a saved flow to replay"
    )
    group.add_argument(
        "--replay-ignore-param",
        action="append", dest="replay_ignore_params", type=str,
        help="Request's parameters to be ignored while searching for a saved flow to replay"
           "Can be passed multiple times."
    )

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
        help="Replacement pattern, where the replacement clause is a path to a file."
    )

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

    group = parser.add_argument_group(
        "Proxy Authentication",
        """
            Specify which users are allowed to access the proxy and the method
            used for authenticating them.
        """
    )
    user_specification_group = group.add_mutually_exclusive_group()
    user_specification_group.add_argument(
        "--nonanonymous",
        action="store_true", dest="auth_nonanonymous",
        help="Allow access to any user long as a credentials are specified."
    )

    user_specification_group.add_argument(
        "--singleuser",
        action="store", dest="auth_singleuser", type=str,
        metavar="USER",
        help="Allows access to a a single user, specified in the form username:password."
    )
    user_specification_group.add_argument(
        "--htpasswd",
        action="store", dest="auth_htpasswd", type=str,
        metavar="PATH",
        help="Allow access to users specified in an Apache htpasswd file."
    )

    config.ssl_option_group(parser)
