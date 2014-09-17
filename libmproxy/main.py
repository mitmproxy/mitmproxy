from __future__ import print_function, absolute_import
import argparse
import os
import signal
import sys
import netlib.version
from . import version, cmdline
from .proxy import process_proxy_options, ProxyServerError
from .proxy.server import DummyServer, ProxyServer


def check_versions():
    """
    Having installed a wrong version of pyOpenSSL or netlib is unfortunately a very common source of error.
    Check before every start that both versions are somewhat okay.
    """
    # We don't introduce backward-incompatible changes in patch versions. Only consider major and minor version.
    if netlib.version.IVERSION[:2] != version.IVERSION[:2]:
        print(
            "Warning: You are using mitmdump %s with netlib %s. "
            "Most likely, that doesn't work - please upgrade!" % (version.VERSION, netlib.version.VERSION),
            file=sys.stderr)
    import OpenSSL, inspect

    v = tuple([int(x) for x in OpenSSL.__version__.split(".")][:2])
    if v < (0, 14):
        print("You are using an outdated version of pyOpenSSL: mitmproxy requires pyOpenSSL 0.14 or greater.",
              file=sys.stderr)
        # Some users apparently have multiple versions of pyOpenSSL installed. Report which one we got.
        pyopenssl_path = os.path.dirname(inspect.getfile(OpenSSL))
        print("Your pyOpenSSL %s installation is located at %s" % (OpenSSL.__version__, pyopenssl_path),
              file=sys.stderr)
        sys.exit(1)


def assert_utf8_env():
    spec = ""
    for i in ["LANG", "LC_CTYPE", "LC_ALL"]:
        spec += os.environ.get(i, "").lower()
    if "utf" not in spec:
        print("Error: mitmproxy requires a UTF console environment.", file=sys.stderr)
        print("Set your LANG enviroment variable to something like en_US.UTF-8", file=sys.stderr)
        sys.exit(1)


def get_server(dummy_server, options):
    if dummy_server:
        return DummyServer(options)
    else:
        try:
            return ProxyServer(options)
        except ProxyServerError, v:
            print(str(v), file=sys.stderr)
            sys.exit(1)


def mitmproxy_cmdline():
    # Don't import libmproxy.console for mitmdump, urwid is not available on all platforms.
    from . import console
    from .console import palettes

    parser = argparse.ArgumentParser(usage="%(prog)s [options]")
    parser.add_argument('--version', action='version', version=version.NAMEVERSION)
    cmdline.common_options(parser)
    parser.add_argument(
        "--palette", type=str, default="dark",
        action="store", dest="palette",
        help="Select color palette: " + ", ".join(palettes.palettes.keys())
    )
    parser.add_argument(
        "-e",
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

    options = parser.parse_args()
    if options.quiet:
        options.verbose = 0

    proxy_config = process_proxy_options(parser, options)
    console_options = console.Options(**cmdline.get_common_options(options))
    console_options.palette = options.palette
    console_options.eventlog = options.eventlog
    console_options.intercept = options.intercept

    return console_options, proxy_config


def mitmproxy():  # pragma: nocover
    from . import console

    check_versions()
    assert_utf8_env()
    console_options, proxy_config = mitmproxy_cmdline()
    server = get_server(console_options.no_server, proxy_config)

    m = console.ConsoleMaster(server, console_options)
    try:
        m.run()
    except KeyboardInterrupt:
        pass


def mitmdump_cmdline():
    from . import dump

    parser = argparse.ArgumentParser(usage="%(prog)s [options] [filter]")
    parser.add_argument('--version', action='version', version="mitmdump" + " " + version.VERSION)
    cmdline.common_options(parser)
    parser.add_argument(
        "--keepserving",
        action="store_true", dest="keepserving", default=False,
        help="Continue serving after client playback or file read. We exit by default."
    )
    parser.add_argument(
        "-d",
        action="count", dest="flow_detail", default=1,
        help="Increase flow detail display level. Can be passed multiple times."
    )
    parser.add_argument('args', nargs=argparse.REMAINDER)

    options = parser.parse_args()
    if options.quiet:
        options.verbose = 0
        options.flow_detail = 0

    proxy_config = process_proxy_options(parser, options)
    dump_options = dump.Options(**cmdline.get_common_options(options))
    dump_options.flow_detail = options.flow_detail
    dump_options.keepserving = options.keepserving
    dump_options.filtstr = " ".join(options.args) if options.args else None

    return dump_options, proxy_config


def mitmdump():  # pragma: nocover
    from . import dump

    check_versions()
    dump_options, proxy_config = mitmdump_cmdline()
    server = get_server(dump_options.no_server, proxy_config)

    try:
        master = dump.DumpMaster(server, dump_options)

        def cleankill(*args, **kwargs):
            master.shutdown()

        signal.signal(signal.SIGTERM, cleankill)
        master.run()
    except dump.DumpError as e:
        print("mitmdump: %s" % e, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


def mitmweb_cmdline():
    from . import web
    parser = argparse.ArgumentParser(usage="%(prog)s [options]")
    parser.add_argument(
        '--version',
        action='version',
        version="mitmweb" + " " + version.VERSION
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

    cmdline.common_options(parser)
    group = parser.add_argument_group(
        "Filters",
        "See help in mitmproxy for filter expression syntax."
    )
    group.add_argument(
        "-i", "--intercept", action="store",
        type=str, dest="intercept", default=None,
        help="Intercept filter expression."
    )

    options = parser.parse_args()
    if options.quiet:
        options.verbose = 0

    proxy_config = process_proxy_options(parser, options)
    web_options = web.Options(**cmdline.get_common_options(options))
    web_options.intercept = options.intercept
    web_options.wdebug = options.wdebug
    web_options.wiface = options.wiface
    web_options.wport = options.wport
    return web_options, proxy_config


def mitmweb():  # pragma: nocover
    from . import web

    check_versions()
    web_options, proxy_config = mitmweb_cmdline()
    server = get_server(web_options.no_server, proxy_config)

    m = web.WebMaster(server, web_options)
    try:
        m.run()
    except KeyboardInterrupt:
        pass
