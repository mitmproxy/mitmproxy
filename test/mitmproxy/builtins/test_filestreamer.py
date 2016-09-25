from __future__ import absolute_import, print_function, division

from .. import tutils, mastertest

import os.path

from mitmproxy.builtins import filestreamer
from mitmproxy.flow import master, FlowReader
from mitmproxy.flow import state
from mitmproxy import options


class TestStream(mastertest.MasterTest):
    def test_stream(self):
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")

            def r():
                r = FlowReader(open(p, "rb"))
                return list(r.stream())

            s = state.State()
            o = options.Options(
                outfile = (p, "wb")
            )
            m = master.FlowMaster(o, None, s)
            sa = filestreamer.FileStreamer()

            m.addons.add(sa)
            f = tutils.tflow(resp=True)
            m.request(f)
            m.response(f)
            m.addons.remove(sa)

            assert r()[0].response

            m.options.outfile = (p, "ab")

            m.addons.add(sa)
            f = tutils.tflow()
            m.request(f)
            m.addons.remove(sa)
            assert not r()[1].response
