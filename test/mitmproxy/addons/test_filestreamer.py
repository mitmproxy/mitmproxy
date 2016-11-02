from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons

import os.path
from mitmproxy.addons import filestreamer
from mitmproxy import io


def test_stream():
    sa = filestreamer.FileStreamer()
    with taddons.context() as tctx:
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")

            def r():
                x = io.FlowReader(open(p, "rb"))
                return list(x.stream())

            tctx.configure(sa, outfile=(p, "wb"))

            f = tflow.tflow(resp=True)
            sa.request(f)
            sa.response(f)
            tctx.configure(sa, outfile=None)
            assert r()[0].response

            tctx.configure(sa, outfile=(p, "ab"))
            f = tflow.tflow()
            sa.request(f)
            tctx.configure(sa, outfile=None)
            assert not r()[1].response
