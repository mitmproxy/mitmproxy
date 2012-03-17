import optparse
import libpry
from libmproxy import cmdline


class uAll(libpry.AutoTree):
    def test_parse_replace_hook(self):
        x = cmdline.parse_replace_hook("/foo/bar/voing")
        assert x == ("foo", "bar", "voing")

        x = cmdline.parse_replace_hook("/foo/bar/vo/ing/")
        assert x == ("foo", "bar", "vo/ing/")

        x = cmdline.parse_replace_hook("/bar/voing")
        assert x == (".*", "bar", "voing")

        libpry.raises(
            cmdline.ParseReplaceException,
            cmdline.parse_replace_hook,
            "/foo"
        )
        libpry.raises(
            "replacement regex",
            cmdline.parse_replace_hook,
            "patt/[/rep"
        )
        libpry.raises(
            "filter pattern",
            cmdline.parse_replace_hook,
            "/~/foo/rep"
        )
        libpry.raises(
            "empty replacement regex",
            cmdline.parse_replace_hook,
            "//"
        )

    def test_common(self):
        parser = optparse.OptionParser()
        cmdline.common_options(parser)
        opts, args = parser.parse_args(args=[])

        assert cmdline.get_common_options(opts)

        opts.stickycookie_all = True
        opts.stickyauth_all = True
        v = cmdline.get_common_options(opts)
        assert v["stickycookie"] == ".*"
        assert v["stickyauth"] == ".*"

        opts.stickycookie_all = False
        opts.stickyauth_all = False
        opts.stickycookie_filt = "foo"
        opts.stickyauth_filt = "foo"
        v = cmdline.get_common_options(opts)
        assert v["stickycookie"] == "foo"
        assert v["stickyauth"] == "foo"

        opts.replace = ["/foo/bar/voing"]
        v = cmdline.get_common_options(opts)
        assert v["replacements"] == [("foo", "bar", "voing")]

        opts.replace = ["//"]
        libpry.raises(
            "empty replacement regex", 
            cmdline.get_common_options,
            opts
        )

        opts.replace = []
        opts.replace_file = [("/foo/bar/nonexistent")]
        libpry.raises(
            "could not read replace file", 
            cmdline.get_common_options,
            opts
        )

        opts.replace_file = [("/~/bar/nonexistent")]
        libpry.raises(
            "filter pattern", 
            cmdline.get_common_options,
            opts
        )

        opts.replace_file = [("/foo/bar/./data/replace")]
        v = cmdline.get_common_options(opts)["replacements"]
        assert len(v) == 1
        assert v[0][2].strip() == "replacecontents"



tests = [
    uAll()
]

