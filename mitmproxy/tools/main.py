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
from mitmproxy import optmanager  # noqa
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


def process_options(parser, opts, args):
    if args.version:
        print(debug.dump_system_info())
        sys.exit(0)
    if args.quiet or args.options:
        args.verbosity = 0
        args.flow_detail = 0

    adict = {}
    for n in dir(args):
        if n in opts:
            adict[n] = getattr(args, n)
    opts.merge(adict)

    pconf = config.ProxyConfig(opts)
    if opts.server:
        try:
            return server.ProxyServer(pconf)
        except exceptions.ServerException as v:
            print(str(v), file=sys.stderr)
            sys.exit(1)
    else:
        return server.DummyServer(pconf)


def run(MasterKlass, args):  # pragma: no cover
    version_check.check_pyopenssl_version()
    debug.register_info_dumpers()

    opts = options.Options()
    parser = cmdline.mitmdump(opts)
    args = parser.parse_args(args)
    master = None
    try:
        optmanager.load_paths(opts, args.conf)
        server = process_options(parser, opts, args)
        master = MasterKlass(opts, server)
        master.addons.configure_all(opts, opts.keys())
        if args.options:
            print(optmanager.dump_defaults(opts))
            sys.exit(0)
        opts.set(*args.setoptions)

        def cleankill(*args, **kwargs):
            master.shutdown()

        signal.signal(signal.SIGTERM, cleankill)
        master.run()
    except exceptions.OptionsError as e:
        print("%s: %s" % (sys.argv[0], e), file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, RuntimeError):
        pass
    if master is None or getattr(master, "has_errored", None):
        print("%s: errors occurred during run" % sys.argv[0], file=sys.stderr)
        sys.exit(1)


def mitmproxy(args=None):  # pragma: no cover
    if os.name == "nt":
        print("Error: mitmproxy's console interface is not supported on Windows. "
              "You can run mitmdump or mitmweb instead.", file=sys.stderr)
        sys.exit(1)
    assert_utf8_env()

    from mitmproxy.tools import console
    run(console.master.ConsoleMaster, args)


def mitmdump(args=None):  # pragma: no cover
    from mitmproxy.tools import dump
    run(dump.DumpMaster, args)


def mitmweb(args=None):  # pragma: no cover
    from mitmproxy.tools import web
    run(web.master.WebMaster, args)
