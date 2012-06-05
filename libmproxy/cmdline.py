# Copyright (C) 2012  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import proxy
import optparse, re, filt


class ParseReplaceException(Exception): pass
class OptionException(Exception): pass


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
        ParseReplaceException on error.
    """
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        patt = ".*"
        regex, replacement = parts
    elif len(parts) == 3:
        patt, regex, replacement = parts
    else:
        raise ParseReplaceException("Malformed replacement specifier - too few clauses: %s"%s)

    if not regex:
        raise ParseReplaceException("Empty replacement regex: %s"%str(patt))

    try:
        re.compile(regex)
    except re.error, e:
        raise ParseReplaceException("Malformed replacement regex: %s"%str(e.message))

    if not filt.parse(patt):
        raise ParseReplaceException("Malformed replacement filter pattern: %s"%patt)

    return patt, regex, replacement


def get_common_options(options):
    stickycookie, stickyauth = None, None
    if options.stickycookie_all:
        stickycookie = ".*"
    elif options.stickycookie_filt:
        stickycookie = options.stickycookie_filt

    if options.stickyauth_all:
        stickyauth = ".*"
    elif options.stickyauth_filt:
        stickyauth = options.stickyauth_filt

    reps = []
    for i in options.replace:
        try:
            p = parse_replace_hook(i)
        except ParseReplaceException, e:
            raise OptionException(e.message)
        reps.append(p)
    for i in options.replace_file:
        try:
            patt, rex, path = parse_replace_hook(i)
        except ParseReplaceException, e:
            raise OptionException(e.message)
        try:
            v = open(path, "r").read()
        except IOError, e:
            raise OptionException("Could not read replace file: %s"%path)
        reps.append((patt, rex, v))

    return dict(
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
        server_replay = options.server_replay,
        script = options.script,
        stickycookie = stickycookie,
        stickyauth = stickyauth,
        wfile = options.wfile,
        verbosity = options.verbose,
        nopop = options.nopop,
    )


def common_options(parser):
    parser.add_option(
        "-a",
        action="store", type = "str", dest="addr", default='',
        help = "Address to bind proxy to (defaults to all interfaces)"
    )
    parser.add_option(
        "--anticache",
        action="store_true", dest="anticache", default=False,
        help="Strip out request headers that might cause the server to return 304-not-modified."
    )
    parser.add_option(
        "--confdir",
        action="store", type = "str", dest="confdir", default='~/.mitmproxy',
        help = "Configuration directory. (~/.mitmproxy)"
    )
    parser.add_option(
        "-e",
        action="store_true", dest="eventlog",
        help="Show event log."
    )
    parser.add_option(
        "-n",
        action="store_true", dest="no_server",
        help="Don't start a proxy server."
    )
    parser.add_option(
        "-p",
        action="store", type = "int", dest="port", default=8080,
        help = "Proxy service port."
    )
    parser.add_option(
        "-P",
        action="store", dest="reverse_proxy", default=None,
        help="Reverse proxy to upstream server: http[s]://host[:port]"
    )
    parser.add_option(
        "-q",
        action="store_true", dest="quiet",
        help="Quiet."
    )
    parser.add_option(
        "-r",
        action="store", dest="rfile", default=None,
        help="Read flows from file."
    )
    parser.add_option(
        "-s",
        action="store", dest="script", default=None,
        help="Run a script."
    )
    parser.add_option(
        "-t",
        action="store_true", dest="stickycookie_all", default=None,
        help="Set sticky cookie for all requests."
    )
    parser.add_option(
        "-T",
        action="store", dest="stickycookie_filt", default=None, metavar="FILTER",
        help="Set sticky cookie filter. Matched against requests."
    )
    parser.add_option(
        "-u",
        action="store_true", dest="stickyauth_all", default=None,
        help="Set sticky auth for all requests."
    )
    parser.add_option(
        "-U",
        action="store", dest="stickyauth_filt", default=None, metavar="FILTER",
        help="Set sticky auth filter. Matched against requests."
    )
    parser.add_option(
        "-v",
        action="count", dest="verbose", default=1,
        help="Increase verbosity. Can be passed multiple times."
    )
    parser.add_option(
        "-w",
        action="store", dest="wfile", default=None,
        help="Write flows to file."
    )
    parser.add_option(
        "-z",
        action="store_true", dest="anticomp", default=False,
        help="Try to convince servers to send us un-compressed data."
    )
    parser.add_option(
        "-Z",
        action="store", dest="body_size_limit", default=None,
        metavar="SIZE",
        help="Byte size limit of HTTP request and response bodies."\
             " Understands k/m/g suffixes, i.e. 3m for 3 megabytes."
    )
    parser.add_option(
        "--cert-wait-time", type="float",
        action="store", dest="cert_wait_time", default=0,
        help="Wait for specified number of seconds after a new cert is generated. This can smooth over small discrepancies between the client and server times."
    )
    parser.add_option(
        "--upstream-cert", default=False,
        action="store_true", dest="upstream_cert",
        help="Connect to upstream server to look up certificate details."
    )

    group = optparse.OptionGroup(parser, "Client Replay")
    group.add_option(
        "-c",
        action="store", dest="client_replay", default=None, metavar="PATH",
        help="Replay client requests from a saved file."
    )
    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "Server Replay")
    group.add_option(
        "-S",
        action="store", dest="server_replay", default=None, metavar="PATH",
        help="Replay server responses from a saved file."
    )
    group.add_option(
        "-k",
        action="store_true", dest="kill", default=False,
        help="Kill extra requests during replay."
    )
    group.add_option(
        "--rheader",
        action="append", dest="rheaders", type="str",
        help="Request headers to be considered during replay. "
           "Can be passed multiple times."
    )
    group.add_option(
        "--norefresh",
        action="store_true", dest="norefresh", default=False,
        help= "Disable response refresh, "
        "which updates times in cookies and headers for replayed responses."
    )
    group.add_option(
        "--no-pop",
        action="store_true", dest="nopop", default=False,
        help="Disable response pop from response flow. "
        "This makes it possible to replay same response multiple times."
    )
    parser.add_option_group(group)

    group = optparse.OptionGroup(
        parser,
        "Replacements",
        """
            Replacements are of the form "/pattern/regex/replacement", where
            the separator can be any character. Please see the documentation
            for more information.
        """.strip()
    )
    group.add_option(
        "--replace",
        action="append", type="str", dest="replace", default=[],
        metavar="PATTERN",
        help="Replacement pattern."
    )
    group.add_option(
        "--replace-from-file",
        action="append", type="str", dest="replace_file", default=[],
        metavar="PATTERN",
        help="Replacement pattern, where the replacement clause is a path to a file."
    )
    parser.add_option_group(group)

    proxy.certificate_option_group(parser)
