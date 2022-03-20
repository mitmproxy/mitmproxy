import argparse
import asyncio
import os
import signal
import sys
import typing

from mitmproxy import exceptions, master
from mitmproxy import options
from mitmproxy import optmanager
from mitmproxy.tools import cmdline
from mitmproxy.utils import debug, arg_check


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
        # also reduce log verbosity if --options or --commands is passed,
        # we don't want log messages from regular startup then.
        args.termlog_verbosity = 'error'
        args.flow_detail = 0
    if args.verbose:
        args.termlog_verbosity = 'debug'
        args.flow_detail = 2

    adict = {}
    for n in dir(args):
        if n in opts:
            adict[n] = getattr(args, n)
    opts.merge(adict)


T = typing.TypeVar("T", bound=master.Master)


def run(
        master_cls: typing.Type[T],
        make_parser: typing.Callable[[options.Options], argparse.ArgumentParser],
        arguments: typing.Sequence[str],
        extra: typing.Callable[[typing.Any], dict] = None
) -> T:  # pragma: no cover
    """
        extra: Extra argument processing callable which returns a dict of
        options.
    """
    async def main() -> T:
        debug.register_info_dumpers()

        opts = options.Options()
        master = master_cls(opts)

        parser = make_parser(opts)

        # To make migration from 2.x to 3.0 bearable.
        if "-R" in sys.argv and sys.argv[sys.argv.index("-R") + 1].startswith("http"):
            print("To use mitmproxy in reverse mode please use --mode reverse:SPEC instead")

        try:
            args = parser.parse_args(arguments)
        except SystemExit:
            arg_check.check()
            sys.exit(1)

        try:
            opts.set(*args.setoptions, defer=True)
            optmanager.load_paths(
                opts,
                os.path.join(opts.confdir, "config.yaml"),
                os.path.join(opts.confdir, "config.yml"),
            )
            process_options(parser, opts, args)

            if args.options:
                optmanager.dump_defaults(opts, sys.stdout)
                sys.exit(0)
            if args.commands:
                master.commands.dump()
                sys.exit(0)
            if extra:
                if args.filter_args:
                    master.log.info(f"Only processing flows that match \"{' & '.join(args.filter_args)}\"")
                opts.update(**extra(args))

        except exceptions.OptionsError as e:
            print("{}: {}".format(sys.argv[0], e), file=sys.stderr)
            sys.exit(1)

        loop = asyncio.get_running_loop()

        def _sigint(*_):
            loop.call_soon_threadsafe(getattr(master, "prompt_for_exit", master.shutdown))

        def _sigterm(*_):
            loop.call_soon_threadsafe(master.shutdown)

        # We can't use loop.add_signal_handler because that's not available on Windows' Proactorloop,
        # but signal.signal just works fine for our purposes.
        signal.signal(signal.SIGINT, _sigint)
        signal.signal(signal.SIGTERM, _sigterm)

        await master.run()
        return master

    return asyncio.run(main())


def mitmproxy(args=None) -> typing.Optional[int]:  # pragma: no cover
    if os.name == "nt":
        import urwid
        urwid.set_encoding("utf8")
    else:
        assert_utf8_env()
    from mitmproxy.tools import console
    run(console.master.ConsoleMaster, cmdline.mitmproxy, args)
    return None


def mitmdump(args=None) -> typing.Optional[int]:  # pragma: no cover
    from mitmproxy.tools import dump

    def extra(args):
        if args.filter_args:
            v = " ".join(args.filter_args)
            return dict(
                save_stream_filter=v,
                readfile_filter=v,
                dumper_filter=v,
            )
        return {}

    run(dump.DumpMaster, cmdline.mitmdump, args, extra)
    return None


def mitmweb(args=None) -> typing.Optional[int]:  # pragma: no cover
    from mitmproxy.tools import web
    run(web.master.WebMaster, cmdline.mitmweb, args)
    return None
