from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons

import os.path
from mitmproxy import io
from mitmproxy import exceptions
from mitmproxy.tools import dump
from mitmproxy.addons import streamfile


def test_configure():
    sa = streamfile.StreamFile()
    with taddons.context(options=dump.Options()) as tctx:
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")
            tutils.raises(
                exceptions.OptionsError,
                tctx.configure, sa, streamfile=tdir
            )
            tutils.raises(
                "invalid filter",
                tctx.configure, sa, streamfile=p, filtstr="~~"
            )
            tctx.configure(sa, filtstr="foo")
            assert sa.filt
            tctx.configure(sa, filtstr=None)
            assert not sa.filt


def rd(p):
    x = io.FlowReader(open(p, "rb"))
    return list(x.stream())


def test_tcp():
    sa = streamfile.StreamFile()
    with taddons.context() as tctx:
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")
            tctx.configure(sa, streamfile=p)

            tt = tflow.ttcpflow()
            sa.tcp_start(tt)
            sa.tcp_end(tt)
            tctx.configure(sa, streamfile=None)
            assert rd(p)


def test_simple():
    sa = streamfile.StreamFile()
    with taddons.context() as tctx:
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")

            tctx.configure(sa, streamfile=p)

            f = tflow.tflow(resp=True)
            sa.request(f)
            sa.response(f)
            tctx.configure(sa, streamfile=None)
            assert rd(p)[0].response

            tctx.configure(sa, streamfile=p, streamfile_append=True)
            f = tflow.tflow()
            sa.request(f)
            tctx.configure(sa, streamfile=None)
            assert not rd(p)[1].response
