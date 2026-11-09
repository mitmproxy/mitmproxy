from __future__ import annotations

import argparse
import asyncio
import copy
import logging
import os
import signal
import sys
from collections.abc import Callable
from collections.abc import Sequence
from typing import Any
from typing import TypeVar

from mitmproxy import exceptions
from mitmproxy import master
from mitmproxy import options
from mitmproxy import optmanager
from mitmproxy.tools import cmdline
from mitmproxy.utils import arg_check
from mitmproxy.utils import debug


def process_options(parser, opts, args):
    if args.version:
        print(debug.dump_system_info())
        sys.exit(0)
    if args.quiet or args.options or args.commands:
        # also reduce log verbosity if --options or --commands is passed,
        # we don't want log messages from regular startup then.
        args.termlog_verbosity = "error"
        args.flow_detail = 0
    if args.verbose:
        args.termlog_verbosity = "debug"
        args.flow_detail = 2

    adict = {
        key: val for key, val in vars(args).items() if key in opts and val is not None
    }
    opts.update(**adict)


def apply_startup_options(opts: options.Options, setoptions: Sequence[str]) -> None:
    """
    Apply the --set options and the config file in the resulting confdir.

    Both are worked out on a copy of the options first and then applied in a
    single update, so that addons only see the final values. Otherwise an addon
    reacting to --set confdir=... runs before options from that directory's
    config file (such as cert_passphrase) are in place. Precedence is
    unchanged: the config file overrides --set.
    """
    staged = copy.deepcopy(opts)
    staged.set(*setoptions, defer=True)
    optmanager.load_paths(
        staged,
        os.path.join(staged.confdir, "config.yaml"),
        os.path.join(staged.confdir, "config.yml"),
    )
    opts.deferred.update(staged.deferred)
    opts.update(
        **{
            k: getattr(staged, k)
            for k in staged.keys()
            if getattr(staged, k) != getattr(opts, k)
        }
    )


T = TypeVar("T", bound=master.Master)


def run(
    master_cls: type[T],
    make_parser: Callable[[options.Options], argparse.ArgumentParser],
    arguments: Sequence[str],
    extra: Callable[[Any], dict] | None = None,
) -> T:  # pragma: no cover
    """
    extra: Extra argument processing callable which returns a dict of
    options.
    """

    async def main() -> T:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("tornado").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("hpack").setLevel(logging.WARNING)
        logging.getLogger("urwid").setLevel(logging.INFO)
        logging.getLogger("quic").setLevel(
            logging.WARNING
        )  # aioquic uses a different prefix...
        debug.register_info_dumpers()

        opts = options.Options()
        master = master_cls(opts)

        parser = make_parser(opts)

        # To make migration from 2.x to 3.0 bearable.
        if "-R" in sys.argv and sys.argv[sys.argv.index("-R") + 1].startswith("http"):
            print(
                "To use mitmproxy in reverse mode please use --mode reverse:SPEC instead"
            )

        try:
            args = parser.parse_args(arguments)
        except SystemExit:
            arg_check.check()
            sys.exit(1)

        try:
            apply_startup_options(opts, args.setoptions)
            process_options(parser, opts, args)

            if args.options:
                # Load custom addons so that their options are registered
                if sl := master.addons.get("scriptloader"):
                    for s in sl.addons:
                        if s.ns is None:
                            s.loadscript()
                optmanager.dump_defaults(opts, sys.stdout)
                sys.exit(0)
            if args.commands:
                master.commands.dump()
                sys.exit(0)
            if extra:
                if args.filter_args:
                    logging.info(
                        f'Only processing flows that match "{" & ".join(args.filter_args)}"'
                    )
                opts.update(**extra(args))

        except exceptions.OptionsError as e:
            print(f"{sys.argv[0]}: {e}", file=sys.stderr)
            sys.exit(1)

        loop = asyncio.get_running_loop()

        def _sigint(*_):
            loop.call_soon_threadsafe(
                getattr(master, "prompt_for_exit", master.shutdown)
            )

        def _sigterm(*_):
            loop.call_soon_threadsafe(master.shutdown)

        try:
            # Prefer loop.add_signal_handler where it is available
            # https://github.com/mitmproxy/mitmproxy/issues/7128
            loop.add_signal_handler(signal.SIGINT, _sigint)
            loop.add_signal_handler(signal.SIGTERM, _sigterm)
        except NotImplementedError:
            # Fall back to `signal.signal` for platforms where that is not available (Windows' Proactorloop)
            signal.signal(signal.SIGINT, _sigint)
            signal.signal(signal.SIGTERM, _sigterm)

        # to fix the issue mentioned https://github.com/mitmproxy/mitmproxy/issues/6744
        # by setting SIGPIPE to SIG_IGN, the process will not terminate and continue to run
        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)

        await master.run()
        return master

    return asyncio.run(main())


def mitmproxy(args=None) -> int | None:  # pragma: no cover
    from mitmproxy.tools import console

    run(console.master.ConsoleMaster, cmdline.mitmproxy, args)
    return None


def mitmdump(args=None) -> int | None:  # pragma: no cover
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


def mitmweb(args=None) -> int | None:  # pragma: no cover
    from mitmproxy.tools import web

    run(web.master.WebMaster, cmdline.mitmweb, args)
    return None
