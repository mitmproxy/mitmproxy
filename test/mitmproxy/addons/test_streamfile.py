import pytest

from mitmproxy.test import taddons
from mitmproxy.test import tflow

from mitmproxy import io
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy.addons import streamfile


def test_configure(tmpdir):
    sa = streamfile.StreamFile()
    with taddons.context(options=options.Options()) as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(sa, streamfile=str(tmpdir))
        with pytest.raises(Exception, match="Invalid filter"):
            tctx.configure(
                sa, streamfile=str(tmpdir.join("foo")), streamfile_filter="~~"
            )
        tctx.configure(sa, streamfile_filter="foo")
        assert sa.filt
        tctx.configure(sa, streamfile_filter=None)
        assert not sa.filt


def rd(p):
    x = io.FlowReader(open(p, "rb"))
    return list(x.stream())


def test_tcp(tmpdir):
    sa = streamfile.StreamFile()
    with taddons.context() as tctx:
        p = str(tmpdir.join("foo"))
        tctx.configure(sa, streamfile=p)

        tt = tflow.ttcpflow()
        sa.tcp_start(tt)
        sa.tcp_end(tt)
        tctx.configure(sa, streamfile=None)
        assert rd(p)


def test_simple(tmpdir):
    sa = streamfile.StreamFile()
    with taddons.context() as tctx:
        p = str(tmpdir.join("foo"))

        tctx.configure(sa, streamfile=p)

        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, streamfile=None)
        assert rd(p)[0].response

        tctx.configure(sa, streamfile="+" + p)
        f = tflow.tflow()
        sa.request(f)
        tctx.configure(sa, streamfile=None)
        assert not rd(p)[1].response
