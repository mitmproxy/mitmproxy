from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons

import os.path
from mitmproxy import io
from mitmproxy import exceptions
from mitmproxy.tools import dump
from mitmproxy.addons import filestreamer


def test_configure():
    sa = filestreamer.FileStreamer()
    with taddons.context(options=dump.Options()) as tctx:
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")
            tutils.raises(
                exceptions.OptionsError,
                tctx.configure, sa, outfile=(tdir, "ab")
            )
            tutils.raises(
                "invalid filter",
                tctx.configure, sa, outfile=(p, "ab"), filtstr="~~"
            )
            tutils.raises(
                "invalid mode",
                tctx.configure, sa, outfile=(p, "xx")
            )


def rd(p):
    x = io.FlowReader(open(p, "rb"))
    return list(x.stream())


def test_tcp():
    sa = filestreamer.FileStreamer()
    with taddons.context() as tctx:
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")
            tctx.configure(sa, outfile=(p, "wb"))

            tt = tflow.ttcpflow()
            sa.tcp_start(tt)
            sa.tcp_end(tt)
            tctx.configure(sa, outfile=None)
            assert rd(p)


def test_simple():
    sa = filestreamer.FileStreamer()
    with taddons.context() as tctx:
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")

            tctx.configure(sa, outfile=(p, "wb"))

            f = tflow.tflow(resp=True)
            sa.request(f)
            sa.response(f)
            tctx.configure(sa, outfile=None)
            assert rd(p)[0].response

            tctx.configure(sa, outfile=(p, "ab"))
            f = tflow.tflow()
            sa.request(f)
            tctx.configure(sa, outfile=None)
            assert not rd(p)[1].response

