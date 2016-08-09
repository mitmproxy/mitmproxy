from __future__ import absolute_import, print_function, division

import os
import signal
import sys

from six.moves import _thread  # PY3: We only need _thread.error, which is an alias of RuntimeError in 3.3+

from mitmproxy import cmdline
from mitmproxy import exceptions
from mitmproxy.proxy import config
from mitmproxy.proxy import server
from netlib import version_check
from netlib import debug


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
    if args.sysinfo:
        print(debug.sysinfo())
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
    from . import console

    version_check.check_pyopenssl_version()
    assert_utf8_env()

    parser = cmdline.mitmproxy()
    args = parser.parse_args(args)

    try:
        console_options = console.master.Options(
            **cmdline.get_common_options(args)
        )
        console_options.palette = args.palette
        console_options.palette_transparent = args.palette_transparent
        console_options.eventlog = args.eventlog
        console_options.follow = args.follow
        console_options.intercept = args.intercept
        console_options.filter = args.filter
        console_options.no_mouse = args.no_mouse

        server = process_options(parser, console_options, args)
        m = console.master.ConsoleMaster(server, console_options)
    except exceptions.OptionsError as e:
        print("mitmproxy: %s" % e, file=sys.stderr)
        sys.exit(1)
    try:
        m.run()
    except (KeyboardInterrupt, _thread.error):
        pass


def mitmdump(args=None):  # pragma: no cover
    from . import dump

    version_check.check_pyopenssl_version()

    parser = cmdline.mitmdump()
    args = parser.parse_args(args)
    if args.quiet:
        args.flow_detail = 0

    master = None
    try:
        dump_options = dump.Options(**cmdline.get_common_options(args))
        dump_options.flow_detail = args.flow_detail
        dump_options.keepserving = args.keepserving
        dump_options.filtstr = " ".join(args.args) if args.args else None
        server = process_options(parser, dump_options, args)
        master = dump.DumpMaster(server, dump_options)

        def cleankill(*args, **kwargs):
            master.shutdown()

        signal.signal(signal.SIGTERM, cleankill)
        master.run()
    except (dump.DumpError, exceptions.OptionsError) as e:
        print("mitmdump: %s" % e, file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, _thread.error):
        pass
    if master is None or master.has_errored:
        print("mitmdump: errors occurred during run", file=sys.stderr)
        sys.exit(1)


def mitmweb(args=None):  # pragma: no cover
    from . import web

    version_check.check_pyopenssl_version()

    parser = cmdline.mitmweb()

    args = parser.parse_args(args)

    try:
        web_options = web.master.Options(**cmdline.get_common_options(args))
        web_options.intercept = args.intercept
        web_options.wdebug = args.wdebug
        web_options.wiface = args.wiface
        web_options.wport = args.wport
        web_options.wsingleuser = args.wsingleuser
        web_options.whtpasswd = args.whtpasswd
        web_options.process_web_options(parser)

        server = process_options(parser, web_options, args)
        m = web.master.WebMaster(server, web_options)
    except exceptions.OptionsError as e:
        print("mitmweb: %s" % e, file=sys.stderr)
        sys.exit(1)
    try:
        m.run()
    except (KeyboardInterrupt, _thread.error):
        pass
