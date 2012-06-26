import optparse
from libmproxy import cmdline
import tutils


def test_parse_replace_hook():
    x = cmdline.parse_replace_hook("/foo/bar/voing")
    assert x == ("foo", "bar", "voing")

    x = cmdline.parse_replace_hook("/foo/bar/vo/ing/")
    assert x == ("foo", "bar", "vo/ing/")

    x = cmdline.parse_replace_hook("/bar/voing")
    assert x == (".*", "bar", "voing")

    tutils.raises(
        cmdline.ParseReplaceException,
        cmdline.parse_replace_hook,
        "/foo"
    )
    tutils.raises(
        "replacement regex",
        cmdline.parse_replace_hook,
        "patt/[/rep"
    )
    tutils.raises(
        "filter pattern",
        cmdline.parse_replace_hook,
        "/~/foo/rep"
    )
    tutils.raises(
        "empty replacement regex",
        cmdline.parse_replace_hook,
        "//"
    )

def test_common():
    parser = optparse.OptionParser()
    cmdline.common_options(parser)
    opts, args = parser.parse_args(args=[])

    assert cmdline.get_common_options(opts)

    opts.stickycookie_filt = "foo"
    opts.stickyauth_filt = "foo"
    v = cmdline.get_common_options(opts)
    assert v["stickycookie"] == "foo"
    assert v["stickyauth"] == "foo"

    opts.replace = ["/foo/bar/voing"]
    v = cmdline.get_common_options(opts)
    assert v["replacements"] == [("foo", "bar", "voing")]

    opts.replace = ["//"]
    tutils.raises(
        "empty replacement regex",
        cmdline.get_common_options,
        opts
    )

    opts.replace = []
    opts.replace_file = [("/foo/bar/nonexistent")]
    tutils.raises(
        "could not read replace file",
        cmdline.get_common_options,
        opts
    )

    opts.replace_file = [("/~/bar/nonexistent")]
    tutils.raises(
        "filter pattern",
        cmdline.get_common_options,
        opts
    )

    p = tutils.test_data.path("data/replace")
    opts.replace_file = [("/foo/bar/%s"%p)]
    v = cmdline.get_common_options(opts)["replacements"]
    assert len(v) == 1
    assert v[0][2].strip() == "replacecontents"

