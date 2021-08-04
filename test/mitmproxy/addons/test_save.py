import pytest

from mitmproxy.test import taddons
from mitmproxy.test import tflow

from mitmproxy import io
from mitmproxy import exceptions
from mitmproxy.addons import save
from mitmproxy.addons import view


def test_configure(tmpdir):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(sa, save_stream_file=str(tmpdir))
        with pytest.raises(Exception, match="Invalid filter"):
            tctx.configure(
                sa, save_stream_file=str(tmpdir.join("foo")), save_stream_filter="~~"
            )
        tctx.configure(sa, save_stream_filter="foo")
        assert sa.filt
        tctx.configure(sa, save_stream_filter=None)
        assert not sa.filt


def rd(p):
    with open(p, "rb") as f:
        x = io.FlowReader(f)
        return list(x.stream())


def test_tcp(tmpdir):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmpdir.join("foo"))
        tctx.configure(sa, save_stream_file=p)

        tt = tflow.ttcpflow()
        sa.tcp_start(tt)
        sa.tcp_end(tt)

        tt = tflow.ttcpflow()
        sa.tcp_start(tt)
        sa.tcp_error(tt)

        tctx.configure(sa, save_stream_file=None)
        assert len(rd(p)) == 2


def test_websocket(tmpdir):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmpdir.join("foo"))
        tctx.configure(sa, save_stream_file=p)

        f = tflow.twebsocketflow()
        sa.request(f)
        sa.websocket_end(f)

        f = tflow.twebsocketflow()
        sa.request(f)
        sa.websocket_end(f)

        tctx.configure(sa, save_stream_file=None)
        assert len(rd(p)) == 2


def test_save_command(tmpdir):
    sa = save.Save()
    with taddons.context() as tctx:
        p = str(tmpdir.join("foo"))
        sa.save([tflow.tflow(resp=True)], p)
        assert len(rd(p)) == 1
        sa.save([tflow.tflow(resp=True)], p)
        assert len(rd(p)) == 1
        sa.save([tflow.tflow(resp=True)], "+" + p)
        assert len(rd(p)) == 2

        with pytest.raises(exceptions.CommandError):
            sa.save([tflow.tflow(resp=True)], str(tmpdir))

        v = view.View()
        tctx.master.addons.add(v)
        tctx.master.addons.add(sa)
        tctx.master.commands.execute("save.file @shown %s" % p)


def test_simple(tmpdir):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmpdir.join("foo"))

        tctx.configure(sa, save_stream_file=p)

        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd(p)[0].response

        tctx.configure(sa, save_stream_file="+" + p)
        f = tflow.tflow(err=True)
        sa.request(f)
        sa.error(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd(p)[1].error

        tctx.configure(sa, save_stream_file="+" + p)
        f = tflow.tflow()
        sa.request(f)
        tctx.configure(sa, save_stream_file=None)
        assert not rd(p)[2].response
