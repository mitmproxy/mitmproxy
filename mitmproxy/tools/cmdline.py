import argparse
import os

from mitmproxy import options
from mitmproxy import version


CONFIG_PATH = os.path.join(options.CA_DIR, "config.yaml")


def common_options(parser, opts):
    parser.add_argument(
        '--version',
        action='store_true',
        dest='version',
    )
    parser.add_argument(
        '--shortversion',
        action='version',
        help="show program's short version number and exit",
        version=version.VERSION
    )
    parser.add_argument(
        '--options',
        action='store_true',
        help="Dump all options",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true", dest="quiet",
        help="Quiet."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_const", dest="verbose", const=3,
        help="Increase log verbosity."
    )
    parser.add_argument(
        "--conf",
        type=str, dest="conf", default=CONFIG_PATH,
        metavar="PATH",
        help="Configuration file"
    )

    # Basic options
    opts.make_parser(parser, "mode")
    opts.make_parser(parser, "anticache")
    opts.make_parser(parser, "cadir")
    opts.make_parser(parser, "showhost")
    opts.make_parser(parser, "rfile")
    opts.make_parser(parser, "scripts", metavar="SCRIPT")
    opts.make_parser(parser, "stickycookie", metavar="FILTER")
    opts.make_parser(parser, "stickyauth", metavar="FILTER")
    opts.make_parser(parser, "streamfile")
    opts.make_parser(parser, "anticomp")
    opts.make_parser(parser, "body_size_limit", metavar="SIZE")
    opts.make_parser(parser, "stream_large_bodies")

    # Proxy options
    group = parser.add_argument_group("Proxy Options")
    opts.make_parser(group, "listen_host")
    opts.make_parser(group, "ignore_hosts", metavar="HOST")
    opts.make_parser(group, "tcp_hosts", metavar="HOST")
    opts.make_parser(group, "no_server")
    opts.make_parser(group, "listen_port", metavar="PORT")

    http2 = group.add_mutually_exclusive_group()
    opts.make_parser(http2, "http2")
    opts.make_parser(http2, "http2_priority")

    websocket = group.add_mutually_exclusive_group()
    opts.make_parser(websocket, "websocket")

    opts.make_parser(group, "upstream_auth", metavar="USER:PASS")
    opts.make_parser(group, "rawtcp")
    opts.make_parser(group, "spoof_source_address")
    opts.make_parser(group, "upstream_bind_address", metavar="ADDR")
    opts.make_parser(group, "keep_host_header")

    # Proxy SSL options
    group = parser.add_argument_group("SSL")
    opts.make_parser(group, "certs", metavar="SPEC")
    opts.make_parser(group, "ciphers_server", metavar="CIPHERS")
    opts.make_parser(group, "ciphers_client", metavar="CIPHERS")
    opts.make_parser(group, "client_certs")
    opts.make_parser(group, "upstream_cert")
    opts.make_parser(group, "add_upstream_certs_to_client_chain")
    opts.make_parser(group, "ssl_insecure")
    opts.make_parser(group, "ssl_verify_upstream_trusted_cadir", metavar="PATH")
    opts.make_parser(group, "ssl_verify_upstream_trusted_ca", metavar="PATH")
    opts.make_parser(group, "ssl_version_client", metavar="VERSION")
    opts.make_parser(group, "ssl_version_server", metavar="VERSION")

    # Onboarding app
    group = parser.add_argument_group("Onboarding App")
    opts.make_parser(group, "onboarding")
    opts.make_parser(group, "onboarding_host", metavar="HOST")
    opts.make_parser(group, "onboarding_port", metavar="PORT")

    # Client replay
    group = parser.add_argument_group("Client Replay")
    opts.make_parser(group, "client_replay", metavar="PATH")

    # Server replay
    group = parser.add_argument_group("Server Replay")
    opts.make_parser(group, "server_replay", metavar="PATH")
    opts.make_parser(group, "replay_kill_extra")
    opts.make_parser(group, "server_replay_use_headers", metavar="HEADER")
    opts.make_parser(group, "refresh_server_playback")
    opts.make_parser(group, "server_replay_nopop")

    payload = group.add_mutually_exclusive_group()
    opts.make_parser(payload, "server_replay_ignore_content")
    opts.make_parser(payload, "server_replay_ignore_payload_params")
    opts.make_parser(payload, "server_replay_ignore_params")
    opts.make_parser(payload, "server_replay_ignore_host")

    # Replacements
    group = parser.add_argument_group(
        "Replacements",
        """
            Replacements are of the form "/pattern/regex/replacement", where
            the separator can be any character. Please see the documentation
            for more information.
        """.strip()
    )
    opts.make_parser(group, "replacements", metavar="PATTERN")
    opts.make_parser(group, "replacement_files", metavar="PATTERN")

    # Set headers
    group = parser.add_argument_group(
        "Set Headers",
        """
            Header specifications are of the form "/pattern/header/value",
            where the separator can be any character. Please see the
            documentation for more information.
        """.strip()
    )
    opts.make_parser(group, "setheaders", metavar="PATTERN")

    # Proxy authentication
    group = parser.add_argument_group(
        "Proxy Authentication",
        """
            Specify which users are allowed to access the proxy and the method
            used for authenticating them.
        """
    ).add_mutually_exclusive_group()
    opts.make_parser(group, "auth_nonanonymous")
    opts.make_parser(group, "auth_singleuser", metavar="USER:PASS")
    opts.make_parser(group, "auth_htpasswd", metavar="PATH")


def mitmproxy(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options]")
    common_options(parser, opts)

    opts.make_parser(parser, "console_palette")
    opts.make_parser(parser, "console_palette_transparent")
    opts.make_parser(parser, "console_eventlog")
    opts.make_parser(parser, "console_focus_follow")
    opts.make_parser(parser, "console_order")
    opts.make_parser(parser, "console_mouse")
    group = parser.add_argument_group(
        "Filters",
        "See help in mitmproxy for filter expression syntax."
    )
    opts.make_parser(group, "intercept", metavar="FILTER")
    opts.make_parser(group, "filter", metavar="FILTER")
    return parser


def mitmdump(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options] [filter]")

    common_options(parser, opts)
    opts.make_parser(parser, "keepserving")
    opts.make_parser(parser, "flow_detail", metavar = "LEVEL")
    parser.add_argument(
        'filter_args',
        nargs="...",
        help="""
            Filter view expression, used to only show flows that match a certain filter.
            See help in mitmproxy for filter expression syntax.
        """
    )
    return parser


def mitmweb(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options]")

    group = parser.add_argument_group("Mitmweb")
    opts.make_parser(group, "web_open_browser")
    opts.make_parser(group, "web_port", metavar="PORT")
    opts.make_parser(group, "web_iface", metavar="INTERFACE")
    opts.make_parser(group, "web_debug")

    common_options(parser, opts)
    group = parser.add_argument_group(
        "Filters",
        "See help in mitmproxy for filter expression syntax."
    )
    opts.make_parser(group, "intercept", metavar="FILTER")
    return parser
