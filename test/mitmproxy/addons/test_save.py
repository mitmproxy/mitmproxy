import bz2
import gzip
import lzma

import pytest

from mitmproxy import exceptions
from mitmproxy import io
from mitmproxy.addons import save
from mitmproxy.addons import view
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_configure(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(sa, save_stream_file=str(tmp_path))
        with pytest.raises(Exception, match="Invalid filter"):
            tctx.configure(
                sa, save_stream_file=str(tmp_path / "foo"), save_stream_filter="~~"
            )
        tctx.configure(sa, save_stream_filter="foo")
        assert sa.filt
        tctx.configure(sa, save_stream_filter=None)
        assert not sa.filt


def rd(p):
    with open(p, "rb") as f:
        x = io.FlowReader(f)
        return list(x.stream())


def rd_gz(p):
    with gzip.open(p, "rb") as f:
        x = io.FlowReader(f)
        return list(x.stream())


def rd_bz2(p):
    with bz2.open(p, "rb") as f:
        x = io.FlowReader(f)
        return list(x.stream())


def rd_xz(p):
    with lzma.open(p, "rb") as f:
        x = io.FlowReader(f)
        return list(x.stream())


def test_tcp(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")
        tctx.configure(sa, save_stream_file=p)

        tt = tflow.ttcpflow()
        sa.tcp_start(tt)
        sa.tcp_end(tt)

        tt = tflow.ttcpflow()
        sa.tcp_start(tt)
        sa.tcp_error(tt)

        tctx.configure(sa, save_stream_file=None)
        assert len(rd(p)) == 2


def test_udp(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")
        tctx.configure(sa, save_stream_file=p)

        tt = tflow.tudpflow()
        sa.udp_start(tt)
        sa.udp_end(tt)

        tt = tflow.tudpflow()
        sa.udp_start(tt)
        sa.udp_error(tt)

        tctx.configure(sa, save_stream_file=None)
        assert len(rd(p)) == 2


def test_dns(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")
        tctx.configure(sa, save_stream_file=p)

        f = tflow.tdnsflow(resp=True)
        sa.dns_request(f)
        sa.dns_response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd(p)[0].response

        tctx.configure(sa, save_stream_file="+" + p)
        f = tflow.tdnsflow(err=True)
        sa.dns_request(f)
        sa.dns_error(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd(p)[1].error

        tctx.configure(sa, save_stream_file="+" + p)
        f = tflow.tdnsflow()
        sa.dns_request(f)
        tctx.configure(sa, save_stream_file=None)
        assert not rd(p)[2].response

        f = tflow.tdnsflow()
        sa.dns_response(f)
        assert len(rd(p)) == 3


def test_websocket(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")
        tctx.configure(sa, save_stream_file=p)

        f = tflow.twebsocketflow()
        sa.request(f)
        sa.websocket_end(f)

        f = tflow.twebsocketflow()
        sa.request(f)
        sa.websocket_end(f)

        tctx.configure(sa, save_stream_file=None)
        assert len(rd(p)) == 2


def test_save_command(tmp_path):
    sa = save.Save()
    with taddons.context() as tctx:
        p = str(tmp_path / "foo")
        sa.save([tflow.tflow(resp=True)], p)
        assert len(rd(p)) == 1
        sa.save([tflow.tflow(resp=True)], p)
        assert len(rd(p)) == 1
        sa.save([tflow.tflow(resp=True)], "+" + p)
        assert len(rd(p)) == 2

        with pytest.raises(exceptions.CommandError):
            sa.save([tflow.tflow(resp=True)], str(tmp_path))

        v = view.View()
        tctx.master.addons.add(v)
        tctx.master.addons.add(sa)
        tctx.master.commands.execute("save.file @shown %s" % p)


def test_simple(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")

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

        f = tflow.tflow()
        sa.response(f)
        assert len(rd(p)) == 3


def test_rotate_stream(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        tctx.configure(sa, save_stream_file=str(tmp_path / "a.txt"))
        f1 = tflow.tflow(resp=True)
        f2 = tflow.tflow(resp=True)
        sa.request(f1)
        sa.response(f1)
        sa.request(f2)  # second request already started.
        tctx.configure(sa, save_stream_file=str(tmp_path / "b.txt"))
        sa.response(f2)
        sa.done()

        assert len(rd(tmp_path / "a.txt")) == 1
        assert len(rd(tmp_path / "b.txt")) == 1


def test_disk_full(tmp_path, monkeypatch, capsys):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        tctx.configure(sa, save_stream_file=str(tmp_path / "foo.txt"))

        def _raise(*_):
            raise OSError("wat")

        monkeypatch.setattr(sa, "maybe_rotate_to_new_file", _raise)

        f = tflow.tflow(resp=True)
        sa.request(f)
        with pytest.raises(SystemExit):
            sa.response(f)

        assert "Error while writing" in capsys.readouterr().err


def test_simple_gzip(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")

        tctx.configure(sa, save_stream_file=p, save_stream_compression="gz")

        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_gz(p)[0].response

        # Test append mode with gzip (concatenated gzip members)
        tctx.configure(sa, save_stream_file="+" + p, save_stream_compression="gz")
        f = tflow.tflow(err=True)
        sa.request(f)
        sa.error(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_gz(p)[1].error


def test_rotate_stream_gzip(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        tctx.configure(
            sa,
            save_stream_file=str(tmp_path / "a"),
            save_stream_compression="gz",
        )
        f1 = tflow.tflow(resp=True)
        f2 = tflow.tflow(resp=True)
        sa.request(f1)
        sa.response(f1)
        sa.request(f2)  # second request already started.
        tctx.configure(sa, save_stream_file=str(tmp_path / "b"))
        sa.response(f2)
        sa.done()

        assert len(rd_gz(tmp_path / "a")) == 1
        assert len(rd_gz(tmp_path / "b")) == 1


def test_tcp_gzip(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")
        tctx.configure(sa, save_stream_file=p, save_stream_compression="gz")

        tt = tflow.ttcpflow()
        sa.tcp_start(tt)
        sa.tcp_end(tt)

        tctx.configure(sa, save_stream_file=None)
        assert len(rd_gz(p)) == 1


def test_simple_bz2(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")

        tctx.configure(sa, save_stream_file=p, save_stream_compression="bz2")
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_bz2(p)[0].response

        # Test append mode (concatenated bz2 streams)
        tctx.configure(sa, save_stream_file="+" + p, save_stream_compression="bz2")
        f = tflow.tflow(err=True)
        sa.request(f)
        sa.error(f)
        tctx.configure(sa, save_stream_file=None)
        flows = rd_bz2(p)
        assert len(flows) == 2
        assert flows[1].error


def test_simple_xz(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")

        tctx.configure(sa, save_stream_file=p, save_stream_compression="xz")
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_xz(p)[0].response

        # Test append mode (concatenated xz streams)
        tctx.configure(sa, save_stream_file="+" + p, save_stream_compression="xz")
        f = tflow.tflow(err=True)
        sa.request(f)
        sa.error(f)
        tctx.configure(sa, save_stream_file=None)
        flows = rd_xz(p)
        assert len(flows) == 2
        assert flows[1].error


def test_compression_level(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        # gz with level
        p = str(tmp_path / "foo_gz")
        tctx.configure(sa, save_stream_file=p, save_stream_compression="gz=1")
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_gz(p)[0].response

        # bz2 with level
        p = str(tmp_path / "foo_bz2")
        tctx.configure(sa, save_stream_file=p, save_stream_compression="bz2=5")
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_bz2(p)[0].response

        # xz with level
        p = str(tmp_path / "foo_xz")
        tctx.configure(sa, save_stream_file=p, save_stream_compression="xz=3")
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_xz(p)[0].response


def test_compression_invalid(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        with pytest.raises(exceptions.OptionsError, match="Invalid compression algorithm"):
            tctx.configure(
                sa,
                save_stream_file=str(tmp_path / "foo"),
                save_stream_compression="zstd",
            )
        with pytest.raises(exceptions.OptionsError, match="Invalid compression level"):
            tctx.configure(
                sa,
                save_stream_file=str(tmp_path / "foo"),
                save_stream_compression="gz=abc",
            )
        with pytest.raises(exceptions.OptionsError, match="Invalid compression level .* for gz"):
            tctx.configure(
                sa,
                save_stream_file=str(tmp_path / "foo"),
                save_stream_compression="gz=10",
            )
        with pytest.raises(exceptions.OptionsError, match="Invalid compression level .* for bz2"):
            tctx.configure(
                sa,
                save_stream_file=str(tmp_path / "foo"),
                save_stream_compression="bz2=0",
            )
        with pytest.raises(exceptions.OptionsError, match="Invalid compression level .* for xz"):
            tctx.configure(
                sa,
                save_stream_file=str(tmp_path / "foo"),
                save_stream_compression="xz=10",
            )


def test_compression_change_at_runtime(tmp_path):
    """Changing compression on an already-open stream without changing the file should error."""
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")

        # Start with gz compression
        tctx.configure(sa, save_stream_file=p, save_stream_compression="gz")
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)

        # Switching compression on the same path should error
        with pytest.raises(Exception, match="Cannot change save_stream_compression"):
            tctx.configure(sa, save_stream_compression="bz2")

        # But changing both file and compression together should work
        p2 = str(tmp_path / "bar")
        tctx.configure(sa, save_stream_file=p2, save_stream_compression="bz2")
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_bz2(p2)[0].response
