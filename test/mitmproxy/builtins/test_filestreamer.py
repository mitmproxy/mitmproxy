from .. import tutils, mastertest

import os.path

from mitmproxy.builtins import filestreamer
from mitmproxy import master
from mitmproxy.flow import io
from mitmproxy import options
from mitmproxy import proxy


class TestStream(mastertest.MasterTest):
    def test_stream(self):
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")

            def r():
                r = io.FlowReader(open(p, "rb"))
                return list(r.stream())

            o = options.Options(
                outfile = (p, "wb")
            )
            m = master.Master(o, proxy.DummyServer())
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
