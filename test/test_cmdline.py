import optparse
import libpry
from libmproxy import cmdline


class uAll(libpry.AutoTree):
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




tests = [
    uAll()
]

