import argparse

from mitmproxy import options
from mitmproxy.tools import cmdline
from mitmproxy.tools import main


def test_common():
    parser = argparse.ArgumentParser()
    opts = options.Options()
    cmdline.common_options(parser, opts)
    args = parser.parse_args(args=[])
    main.process_options(parser, opts, args)


def test_mitmproxy():
    opts = options.Options()
    ap = cmdline.mitmproxy(opts)
    assert ap


def test_mitmdump():
    opts = options.Options()
    ap = cmdline.mitmdump(opts)
    assert ap


def test_mitmweb():
    opts = options.Options()
    ap = cmdline.mitmweb(opts)
    assert ap
