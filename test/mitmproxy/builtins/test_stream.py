from __future__ import absolute_import, print_function, division

from .. import tutils, mastertest

import os.path

from mitmproxy.builtins import stream
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
            m = master.FlowMaster(
                options.Options(
                    outfile = (p, "wb")
                ),
                None,
                s
            )
            sa = stream.Stream()

            m.addons.add(sa)
            f = tutils.tflow(resp=True)
            self.invoke(m, "request", f)
            self.invoke(m, "response", f)
            m.addons.remove(sa)

            assert r()[0].response

            m.options.outfile = (p, "ab")

            m.addons.add(sa)
            f = tutils.tflow()
            self.invoke(m, "request", f)
            m.addons.remove(sa)
            assert not r()[1].response
