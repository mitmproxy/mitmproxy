import argparse
from mitmproxy.tools import cmdline
from mitmproxy.test import tutils


def test_parse_setheaders():
    x = cmdline.parse_setheader("/foo/bar/voing")
    assert x == ("foo", "bar", "voing")


def test_common():
    parser = argparse.ArgumentParser()
    cmdline.common_options(parser)
    opts = parser.parse_args(args=[])

    assert cmdline.get_common_options(opts)

    opts.stickycookie_filt = "foo"
    opts.stickyauth_filt = "foo"
    v = cmdline.get_common_options(opts)
    assert v["stickycookie"] == "foo"
    assert v["stickyauth"] == "foo"

    opts.setheader = ["/foo/bar/voing"]
    v = cmdline.get_common_options(opts)
    assert v["setheaders"] == [("foo", "bar", "voing")]

    opts.setheader = ["//"]
    tutils.raises(
        "empty clause",
        cmdline.get_common_options,
        opts
    )
    opts.setheader = []


def test_mitmproxy():
    ap = cmdline.mitmproxy()
    assert ap


def test_mitmdump():
    ap = cmdline.mitmdump()
    assert ap


def test_mitmweb():
    ap = cmdline.mitmweb()
    assert ap
