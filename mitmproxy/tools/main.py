from __future__ import print_function  # this is here for the version check to work on Python 2.
import sys

if sys.version_info < (3, 5):
    print("#" * 49, file=sys.stderr)
    print("# mitmproxy only supports Python 3.5 and above! #", file=sys.stderr)
    print("#" * 49, file=sys.stderr)

import os  # noqa
import signal  # noqa

from mitmproxy.tools import cmdline  # noqa
from mitmproxy import exceptions  # noqa
from mitmproxy import options  # noqa
from mitmproxy.proxy import config  # noqa
from mitmproxy.proxy import server  # noqa
from mitmproxy.utils import version_check  # noqa
from mitmproxy.utils import debug  # noqa


def assert_utf8_env():
    spec = ""
    for i in ["LANG", "LC_CTYPE", "LC_ALL"]:
        spec += os.environ.get(i, "").lower()
    if "utf" not in spec:
        print(
            "Error: mitmproxy requires a UTF console environment.",
            file=sys.stderr
        )
        print(
            "Set your LANG enviroment variable to something like en_US.UTF-8",
            file=sys.stderr
        )
        sys.exit(1)


def process_options(parser, options, args):
    if args.version:
        print(debug.dump_system_info())
        sys.exit(0)

    debug.register_info_dumpers()
    pconf = config.ProxyConfig(options)
    if options.no_server:
        return server.DummyServer(pconf)
    else:
        try:
            return server.ProxyServer(pconf)
        except exceptions.ServerException as v:
            print(str(v), file=sys.stderr)
            sys.exit(1)


def mitmproxy(args=None):  # pragma: no cover
    if os.name == "nt":
        print("Error: mitmproxy's console interface is not supported on Windows. "
              "You can run mitmdump or mitmweb instead.", file=sys.stderr)
        sys.exit(1)
    from mitmproxy.tools import console

    version_check.check_pyopenssl_version()
    assert_utf8_env()

    parser = cmdline.mitmproxy()
    args = parser.parse_args(args)

    try:
        console_options = options.Options()
        console_options.load_paths(args.conf)
        console_options.merge(cmdline.get_common_options(args))
        console_options.merge(
            dict(
                console_palette = args.console_palette,
                console_palette_transparent = args.console_palette_transparent,
                console_eventlog = args.console_eventlog,
                console_focus_follow = args.console_focus_follow,
                console_no_mouse = args.console_no_mouse,
                console_order = args.console_order,

                filter = args.filter,
                intercept = args.intercept,
            )
        )

        server = process_options(parser, console_options, args)
        m = console.master.ConsoleMaster(console_options, server)
    except exceptions.OptionsError as e:
        print("mitmproxy: %s" % e, file=sys.stderr)
        sys.exit(1)
    try:
        m.run()
    except (KeyboardInterrupt, RuntimeError):
        pass


def mitmdump(args=None):  # pragma: no cover
    from mitmproxy.tools import dump

    version_check.check_pyopenssl_version()

    parser = cmdline.mitmdump()
    args = parser.parse_args(args)
    if args.quiet:
        args.flow_detail = 0

    master = None
    try:
        dump_options = options.Options()
        dump_options.load_paths(args.conf)
        dump_options.merge(cmdline.get_common_options(args))
        dump_options.merge(
            dict(
                flow_detail = args.flow_detail,
                keepserving = args.keepserving,
                filtstr = " ".join(args.filter) if args.filter else None,
            )
        )

        server = process_options(parser, dump_options, args)
        master = dump.DumpMaster(dump_options, server)

        def cleankill(*args, **kwargs):
            master.shutdown()

        signal.signal(signal.SIGTERM, cleankill)
        master.run()
    except (dump.DumpError, exceptions.OptionsError) as e:
        print("mitmdump: %s" % e, file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, RuntimeError):
        pass
    if master is None or master.has_errored:
        print("mitmdump: errors occurred during run", file=sys.stderr)
        sys.exit(1)


def mitmweb(args=None):  # pragma: no cover
    from mitmproxy.tools import web

    version_check.check_pyopenssl_version()

    parser = cmdline.mitmweb()

    args = parser.parse_args(args)

    try:
        web_options = options.Options()
        web_options.load_paths(args.conf)
        web_options.merge(cmdline.get_common_options(args))
        web_options.merge(
            dict(
                intercept = args.intercept,
                web_open_browser = args.web_open_browser,
                web_debug = args.web_debug,
                web_iface = args.web_iface,
                web_port = args.web_port,
            )
        )
        server = process_options(parser, web_options, args)
        m = web.master.WebMaster(web_options, server)
    except exceptions.OptionsError as e:
        print("mitmweb: %s" % e, file=sys.stderr)
        sys.exit(1)
    try:
        m.run()
    except (KeyboardInterrupt, RuntimeError):
        pass
