from __future__ import print_function  # this is here for the version check to work on Python 2.

import sys

if sys.version_info < (3, 5):
    # This must be before any mitmproxy imports, as they already break!
    # Keep all other imports below with the 'noqa' magic comment.
    print("#" * 49, file=sys.stderr)
    print("# mitmproxy only supports Python 3.5 and above! #", file=sys.stderr)
    print("#" * 49, file=sys.stderr)

import argparse  # noqa
import os  # noqa
import signal  # noqa
import typing  # noqa

from mitmproxy.tools import cmdline  # noqa
from mitmproxy import exceptions, master  # noqa
from mitmproxy import options  # noqa
from mitmproxy import optmanager  # noqa
from mitmproxy import proxy  # noqa
from mitmproxy import log  # noqa
from mitmproxy.utils import debug, arg_check  # noqa


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
            "Set your LANG environment variable to something like en_US.UTF-8",
            file=sys.stderr
        )
        sys.exit(1)


def process_options(parser, opts, args):
    if args.version:
        print(debug.dump_system_info())
        sys.exit(0)
    if args.quiet or args.options or args.commands:
        args.verbosity = 'error'
        args.flow_detail = 0

    adict = {}
    for n in dir(args):
        if n in opts:
            adict[n] = getattr(args, n)
    opts.merge(adict)

    return proxy.config.ProxyConfig(opts)


def run(
        master_cls: typing.Type[master.Master],
        make_parser: typing.Callable[[options.Options], argparse.ArgumentParser],
        arguments: typing.Sequence[str],
        extra: typing.Callable[[typing.Any], dict] = None
):  # pragma: no cover
    """
        extra: Extra argument processing callable which returns a dict of
        options.
    """
    debug.register_info_dumpers()

    opts = options.Options()
    master = master_cls(opts)

    parser = make_parser(opts)

    # To make migration from 2.x to 3.0 bearable.
    if "-R" in sys.argv and sys.argv[sys.argv.index("-R") + 1].startswith("http"):
        print("-R is used for specifying replacements.\n"
              "To use mitmproxy in reverse mode please use --mode reverse:SPEC instead")

    try:
        args = parser.parse_args(arguments)
    except SystemExit:
        arg_check.check()
        sys.exit(1)
    try:
        unknown = optmanager.load_paths(opts, args.conf)
        pconf = process_options(parser, opts, args)
        server = None  # type: typing.Any
        if pconf.options.server:
            try:
                server = proxy.server.ProxyServer(pconf)
            except exceptions.ServerException as v:
                print(str(v), file=sys.stderr)
                sys.exit(1)
        else:
            server = proxy.server.DummyServer(pconf)

        master.server = server
        master.addons.trigger("configure", opts.keys())
        master.addons.trigger("tick")
        remaining = opts.update_known(**unknown)
        if remaining and log.log_tier(opts.verbosity) > 1:
            print("Ignored options: %s" % remaining)
        if args.options:
            print(optmanager.dump_defaults(opts))
            sys.exit(0)
        if args.commands:
            master.commands.dump()
            sys.exit(0)
        opts.set(*args.setoptions)
        if extra:
            opts.update(**extra(args))

        def cleankill(*args, **kwargs):
            master.shutdown()

        signal.signal(signal.SIGTERM, cleankill)
        master.run()
    except exceptions.OptionsError as e:
        print("%s: %s" % (sys.argv[0], e), file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, RuntimeError) as e:
        pass
    return master


def mitmproxy(args=None):  # pragma: no cover
    if os.name == "nt":
        print("Error: mitmproxy's console interface is not supported on Windows. "
              "You can run mitmdump or mitmweb instead.", file=sys.stderr)
        sys.exit(1)

    assert_utf8_env()

    from mitmproxy.tools import console
    run(console.master.ConsoleMaster, cmdline.mitmproxy, args)


def mitmdump(args=None):  # pragma: no cover
    from mitmproxy.tools import dump

    def extra(args):
        if args.filter_args:
            v = " ".join(args.filter_args)
            return dict(
                view_filter=v,
                save_stream_filter=v,
            )
        return {}

    m = run(dump.DumpMaster, cmdline.mitmdump, args, extra)
    if m and m.errorcheck.has_errored:
        sys.exit(1)


def mitmweb(args=None):  # pragma: no cover
    from mitmproxy.tools import web
    run(web.master.WebMaster, cmdline.mitmweb, args)
