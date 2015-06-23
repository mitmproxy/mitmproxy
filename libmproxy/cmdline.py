from __future__ import absolute_import
import os
import re
import configargparse
from netlib import http
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
    p = http.parse_url(url)
    if not p or not p[1] or p[0] not in ("http", "https"):
        raise configargparse.ArgumentTypeError(
            "Invalid server specification: %s" % url
        )

    if p[0].lower() == "https":
        ssl = [True, True]
    else:
        ssl = [False, False]

    return ssl + list(p[1:3])


def parse_server_spec_special(url):
    """
    Provides additional support for http2https and https2http schemes.
    """
    normalized_url = re.sub("^https?2", "", url)
    ret = parse_server_spec(normalized_url)
    if url.lower().startswith("https2http"):
        ret[0] = True
    elif url.lower().startswith("http2https"):
        ret[0] = False
    return ret


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
        replay_ignore_content = options.replay_ignore_content,
        replay_ignore_params = options.replay_ignore_params,
        replay_ignore_payload_params = options.replay_ignore_payload_params,
        replay_ignore_host = options.replay_ignore_host
    )


def common_options(parser):
    parser.add_argument(
        '--version',
        action= 'version',
        version= "%(prog)s" + " " + version.VERSION
    )
    parser.add_argument(
        '--shortversion',
        action= 'version',
        help = "show program's short version number and exit",
        version = version.VERSION
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

    group = parser.add_argument_group("Proxy Options")
    # We could make a mutually exclusive group out of -R, -U, -T, but we don't
    # do that because  - --upstream-server should be in that group as well, but
    # it's already in a different group.  - our own error messages are more
    # helpful
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
        "-R", "--reverse",
        action="store",
        type=parse_server_spec_special,
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
    group.add_argument(
        "--spoof",
        action="store_true", dest="spoof_mode", default=False,
        help="Use Host header to connect to HTTP servers."
    )
    group.add_argument(
        "--ssl-spoof",
        action="store_true", dest="ssl_spoof_mode", default=False,
        help="Use TLS SNI to connect to HTTPS servers."
    )
    group.add_argument(
        "--spoofed-port",
        action="store", dest="spoofed_ssl_port", type=int, default=443,
        help="Port number of upstream HTTPS servers in SSL spoof mode."
    )

    group = parser.add_argument_group(
        "Advanced Proxy Options",
        """
            The following options allow a custom adjustment of the proxy
            behavior. Normally, you don't want to use these options directly and
            use the provided wrappers instead (-R, -U, -T).
        """
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

    group = parser.add_argument_group("Client Replay")
    group.add_argument(
        "-c", "--client-replay",
        action="append", dest="client_replay", default=None, metavar="PATH",
        help="Replay client requests from a saved file."
    )

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
        action = "append", type=str, dest="replace_file", default=[],
        metavar = "PATH",
        help = """
            Replacement pattern, where the replacement clause is a path to a
            file.
        """
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
        help="""
            Allows access to a a single user, specified in the form
            username:password.
        """
    )
    user_specification_group.add_argument(
        "--htpasswd",
        action="store", dest="auth_htpasswd", type=str,
        metavar="PATH",
        help="Allow access to users specified in an Apache htpasswd file."
    )

    config.ssl_option_group(parser)


def mitmproxy():
    # Don't import libmproxy.console for mitmdump, urwid is not available on all
    # platforms.
    from .console import palettes

    parser = configargparse.ArgumentParser(
        usage="%(prog)s [options]",
        args_for_setting_config_path = ["--conf"],
        default_config_files = [
            os.path.join(config.CA_DIR, "common.conf"),
            os.path.join(config.CA_DIR, "mitmproxy.conf")
        ],
        add_config_file_help = True,
        add_env_var_help = True
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
        args_for_setting_config_path = ["--conf"],
        default_config_files = [
            os.path.join(config.CA_DIR, "common.conf"),
            os.path.join(config.CA_DIR, "mitmdump.conf")
        ],
        add_config_file_help = True,
        add_env_var_help = True
    )

    common_options(parser)
    parser.add_argument(
        "--keepserving",
        action= "store_true", dest="keepserving", default=False,
        help= """
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
        args_for_setting_config_path = ["--conf"],
        default_config_files = [
            os.path.join(config.CA_DIR, "common.conf"),
            os.path.join(config.CA_DIR, "mitmweb.conf")
        ],
        add_config_file_help = True,
        add_env_var_help = True
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
