import argparse
from mitmproxy.tools import cmdline
from mitmproxy import options


def test_common():
    parser = argparse.ArgumentParser()
    opts = options.Options()
    cmdline.common_options(parser, opts)
    args = parser.parse_args(args=[])

    assert cmdline.get_common_options(args)

    args.stickycookie_filt = "foo"
    args.stickyauth_filt = "foo"
    v = cmdline.get_common_options(args)
    assert v["stickycookie"] == "foo"
    assert v["stickyauth"] == "foo"


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
