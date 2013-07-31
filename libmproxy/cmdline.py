import proxy
import re, filt
import argparse

APP_DOMAIN = "mitm"
APP_IP = "1.1.1.1"

class ParseException(Exception): pass
class OptionException(Exception): pass

def _parse_hook(s):
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        patt = ".*"
        a, b = parts
    elif len(parts) == 3:
        patt, a, b = parts
    else:
        raise ParseException("Malformed hook specifier - too few clauses: %s"%s)

    if not a:
        raise ParseException("Empty clause: %s"%str(patt))

    if not filt.parse(patt):
        raise ParseException("Malformed filter pattern: %s"%patt)

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
        raise ParseException("Malformed replacement regex: %s"%str(e.message))
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


def get_common_options(options):
    stickycookie, stickyauth = None, None
    if options.stickycookie_filt:
        stickycookie = options.stickycookie_filt

    if options.stickyauth_filt:
        stickyauth = options.stickyauth_filt

    reps = []
    for i in options.replace:
        try:
            p = parse_replace_hook(i)
        except ParseException, e:
            raise OptionException(e.message)
        reps.append(p)
    for i in options.replace_file:
        try:
            patt, rex, path = parse_replace_hook(i)
        except ParseException, e:
            raise OptionException(e.message)
        try:
            v = open(path, "rb").read()
        except IOError, e:
            raise OptionException("Could not read replace file: %s"%path)
        reps.append((patt, rex, v))


    setheaders = []
    for i in options.setheader:
        try:
            p = parse_setheader(i)
        except ParseException, e:
            raise OptionException(e.message)
        setheaders.append(p)

    return dict(
        app = options.app,
        app_ip = options.app_ip,
        app_domain = options.app_domain,

        anticache = options.anticache,
        anticomp = options.anticomp,
        client_replay = options.client_replay,
        eventlog = options.eventlog,
        kill = options.kill,
        no_server = options.no_server,
        refresh_server_playback = not options.norefresh,
        rheaders = options.rheaders,
        rfile = options.rfile,
        replacements = reps,
        setheaders = setheaders,
        server_replay = options.server_replay,
        script = options.script,
        stickycookie = stickycookie,
        stickyauth = stickyauth,
        showhost = options.showhost,
        wfile = options.wfile,
        verbosity = options.verbose,
        nopop = options.nopop,
    )


def common_options(parser):
    parser.add_argument(
        "-b",
        action="store", type = str, dest="addr", default='',
        help = "Address to bind proxy to (defaults to all interfaces)"
    )
    parser.add_argument(
        "--anticache",
        action="store_true", dest="anticache", default=False,
        help="Strip out request headers that might cause the server to return 304-not-modified."
    )
    parser.add_argument(
        "--confdir",
        action="store", type = str, dest="confdir", default='~/.mitmproxy',
        help = "Configuration directory. (~/.mitmproxy)"
    )
    parser.add_argument(
        "-e",
        action="store_true", dest="eventlog",
        help="Show event log."
    )
    parser.add_argument(
        "-n",
        action="store_true", dest="no_server",
        help="Don't start a proxy server."
    )
    parser.add_argument(
        "-p",
        action="store", type = int, dest="port", default=8080,
        help = "Proxy service port."
    )
    parser.add_argument(
        "-P",
        action="store", dest="reverse_proxy", default=None,
        help="Reverse proxy to upstream server: http[s]://host[:port]"
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
        action="store", dest="script", default=None,
        help="Run a script."
    )
    parser.add_argument(
        "-t",
        action="store", dest="stickycookie_filt", default=None, metavar="FILTER",
        help="Set sticky cookie filter. Matched against requests."
    )
    parser.add_argument(
        "-T",
        action="store_true", dest="transparent_proxy", default=False,
        help="Set transparent proxy mode."
    )
    parser.add_argument(
        "-u",
        action="store", dest="stickyauth_filt", default=None, metavar="FILTER",
        help="Set sticky auth filter. Matched against requests."
    )
    parser.add_argument(
        "-v",
        action="count", dest="verbose", default=1,
        help="Increase verbosity. Can be passed multiple times."
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
        help="Byte size limit of HTTP request and response bodies."\
             " Understands k/m/g suffixes, i.e. 3m for 3 megabytes."
    )
    parser.add_argument(
        "--host",
        action="store_true", dest="showhost", default=False,
        help="Use the Host header to construct URLs for display."
    )

    parser.add_argument(
        "--no-upstream-cert", default=False,
        action="store_true", dest="no_upstream_cert",
        help="Don't connect to upstream server to look up certificate details."
    )

    group = parser.add_argument_group("Web App")
    group.add_argument(
        "-a",
        action="store_true", dest="app", default=False,
        help="Enable the mitmproxy web app."
    )
    group.add_argument(
        "--appdomain",
        action="store", dest="app_domain", default=APP_DOMAIN, metavar="domain",
        help="Domain to serve the app from."
    )
    group.add_argument(
        "--appip",
        action="store", dest="app_ip", default=APP_IP, metavar="ip",
        help="""IP to serve the app from. Useful for transparent mode, when a DNS
        entry for the app domain is not present."""
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
        help= "Disable response refresh, "
        "which updates times in cookies and headers for replayed responses."
    )
    group.add_argument(
        "--no-pop",
        action="store_true", dest="nopop", default=False,
        help="Disable response pop from response flow. "
        "This makes it possible to replay same response multiple times."
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
            used for authenticating them. These options are ignored if the
            proxy is in transparent or reverse proxy mode.
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
        action="store", dest="auth_htpasswd", type=argparse.FileType('r'),
        metavar="PATH",
        help="Allow access to users specified in an Apache htpasswd file."
    )

    proxy.certificate_option_group(parser)
