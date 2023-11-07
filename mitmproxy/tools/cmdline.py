import argparse


def common_options(parser, opts):
    parser.add_argument(
        "--version",
        action="store_true",
        help="show version number and exit",
        dest="version",
    )
    parser.add_argument(
        "--options",
        action="store_true",
        help="Show all options and their default values",
    )
    parser.add_argument(
        "--commands",
        action="store_true",
        help="Show all commands and their signatures",
    )
    parser.add_argument(
        "--set",
        type=str,
        dest="setoptions",
        default=[],
        action="append",
        metavar="option[=value]",
        help="""
            Set an option. When the value is omitted, booleans are set to true,
            strings and integers are set to None (if permitted), and sequences
            are emptied. Boolean values can be true, false or toggle.
            Sequences are set using multiple invocations to set for
            the same option.
        """,
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", dest="quiet", help="Quiet."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        dest="verbose",
        const="debug",
        help="Increase log verbosity.",
    )

    # Basic options
    opts.make_parser(parser, "mode", short="m")
    opts.make_parser(parser, "anticache")
    opts.make_parser(parser, "showhost")
    opts.make_parser(parser, "rfile", metavar="PATH", short="r")
    opts.make_parser(parser, "scripts", metavar="SCRIPT", short="s")
    opts.make_parser(parser, "stickycookie", metavar="FILTER")
    opts.make_parser(parser, "stickyauth", metavar="FILTER")
    opts.make_parser(parser, "save_stream_file", metavar="PATH", short="w")
    opts.make_parser(parser, "anticomp")

    # Proxy options
    group = parser.add_argument_group("Proxy Options")
    opts.make_parser(group, "listen_host", metavar="HOST")
    opts.make_parser(group, "listen_port", metavar="PORT", short="p")
    opts.make_parser(group, "server", short="n")
    opts.make_parser(group, "ignore_hosts", metavar="HOST")
    opts.make_parser(group, "allow_hosts", metavar="HOST")
    opts.make_parser(group, "tcp_hosts", metavar="HOST")
    opts.make_parser(group, "upstream_auth", metavar="USER:PASS")
    opts.make_parser(group, "proxyauth", metavar="SPEC")
    opts.make_parser(group, "rawtcp")
    opts.make_parser(group, "http2")

    # Proxy SSL options
    group = parser.add_argument_group("SSL")
    opts.make_parser(group, "certs", metavar="SPEC")
    opts.make_parser(group, "cert_passphrase", metavar="PASS")
    opts.make_parser(group, "ssl_insecure", short="k")

    # Client replay
    group = parser.add_argument_group("Client Replay")
    opts.make_parser(group, "client_replay", metavar="PATH", short="C")

    # Server replay
    group = parser.add_argument_group("Server Replay")
    opts.make_parser(group, "server_replay", metavar="PATH", short="S")
    opts.make_parser(group, "server_replay_kill_extra")
    opts.make_parser(group, "server_replay_extra")
    opts.make_parser(group, "server_replay_reuse")
    opts.make_parser(group, "server_replay_refresh")

    # Map Remote
    group = parser.add_argument_group("Map Remote")
    opts.make_parser(group, "map_remote", metavar="PATTERN", short="M")

    # Map Local
    group = parser.add_argument_group("Map Local")
    opts.make_parser(group, "map_local", metavar="PATTERN")

    # Modify Body
    group = parser.add_argument_group("Modify Body")
    opts.make_parser(group, "modify_body", metavar="PATTERN", short="B")

    # Modify headers
    group = parser.add_argument_group("Modify Headers")
    opts.make_parser(group, "modify_headers", metavar="PATTERN", short="H")


def mitmproxy(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options]")
    common_options(parser, opts)

    opts.make_parser(parser, "console_layout")
    opts.make_parser(parser, "console_layout_headers")
    group = parser.add_argument_group(
        "Filters", "See help in mitmproxy for filter expression syntax."
    )
    opts.make_parser(group, "intercept", metavar="FILTER")
    opts.make_parser(group, "view_filter", metavar="FILTER")
    return parser


def mitmdump(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options] [filter]")

    common_options(parser, opts)
    opts.make_parser(parser, "flow_detail", metavar="LEVEL")
    parser.add_argument(
        "filter_args",
        nargs="...",
        help="""
            Filter expression, equivalent to setting both the view_filter
            and save_stream_filter options.
        """,
    )
    return parser


def mitmweb(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options]")

    group = parser.add_argument_group("Mitmweb")
    opts.make_parser(group, "web_open_browser")
    opts.make_parser(group, "web_port", metavar="PORT")
    opts.make_parser(group, "web_host", metavar="HOST")

    common_options(parser, opts)
    group = parser.add_argument_group(
        "Filters", "See help in mitmproxy for filter expression syntax."
    )
    opts.make_parser(group, "intercept", metavar="FILTER")
    return parser
