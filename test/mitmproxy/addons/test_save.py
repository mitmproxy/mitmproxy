from pathlib import Path

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


def rd_zstd(p):
    with open(str(p), "rb") as f:
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


def test_simple_zstd(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "foo")

        tctx.configure(sa, save_stream_file=p, save_stream_compress=True)

        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)
        assert Path(p).read_bytes()[:4] == b"\x28\xb5\x2f\xfd"
        assert rd_zstd(p)[0].response

        # Test append mode (concatenated zstd frames)
        tctx.configure(sa, save_stream_file="+" + p, save_stream_compress=True)
        f = tflow.tflow(err=True)
        sa.request(f)
        sa.error(f)
        tctx.configure(sa, save_stream_file=None)
        assert rd_zstd(p)[1].error


def test_rotate_stream_zstd(tmp_path):
    sa = save.Save()
    with taddons.context(sa) as tctx:
        tctx.configure(
            sa,
            save_stream_file=str(tmp_path / "a"),
            save_stream_compress=True,
        )
        f1 = tflow.tflow(resp=True)
        f2 = tflow.tflow(resp=True)
        sa.request(f1)
        sa.response(f1)
        sa.request(f2)  # second request already started.
        tctx.configure(sa, save_stream_file=str(tmp_path / "b"))
        sa.response(f2)
        sa.done()

        assert len(rd_zstd(tmp_path / "a")) == 1
        assert len(rd_zstd(tmp_path / "b")) == 1


def test_toggle_compression(tmp_path):
    """Toggling save_stream_compress reopens the file with the new format (truncating in wb mode)."""
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "flows")

        # Start without compression
        tctx.configure(sa, save_stream_file=p, save_stream_compress=False)
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)

        # Toggle compression on (same path, non-append mode truncates)
        tctx.configure(sa, save_stream_compress=True)
        f2 = tflow.tflow(resp=True)
        sa.request(f2)
        sa.response(f2)
        tctx.configure(sa, save_stream_file=None)

        # File was reopened with compression; only the second flow remains
        raw = Path(p).read_bytes()
        assert raw[:4] == b"\x28\xb5\x2f\xfd"
        assert len(rd_zstd(p)) == 1


def test_append_compression_mismatch(tmp_path):
    """Appending with mismatched compression raises OptionsError."""
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "flows")

        # Write uncompressed data
        tctx.configure(sa, save_stream_file=p, save_stream_compress=False)
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)

        # Try to append compressed data to uncompressed file
        with pytest.raises(exceptions.OptionsError, match="Cannot append compressed"):
            tctx.configure(sa, save_stream_file="+" + p, save_stream_compress=True)

        # Write compressed data to a new file
        p2 = str(tmp_path / "flows2")
        tctx.configure(sa, save_stream_file=p2, save_stream_compress=True)
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)

        # Try to append uncompressed data to compressed file
        with pytest.raises(exceptions.OptionsError, match="Cannot append uncompressed"):
            tctx.configure(sa, save_stream_file="+" + p2, save_stream_compress=False)


def test_append_compressed_to_compressed(tmp_path):
    """Appending compressed data to an existing compressed file succeeds."""
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "flows")

        # Write first compressed flow
        tctx.configure(sa, save_stream_file=p, save_stream_compress=True)
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)

        # Append second compressed flow
        tctx.configure(sa, save_stream_file="+" + p, save_stream_compress=True)
        f2 = tflow.tflow(resp=True)
        sa.request(f2)
        sa.response(f2)
        tctx.configure(sa, save_stream_file=None)

        # Both flows readable
        assert len(rd_zstd(p)) == 2


def test_append_to_empty_file(tmp_path):
    """Appending to an empty file with compression works regardless of format."""
    sa = save.Save()
    with taddons.context(sa) as tctx:
        p = str(tmp_path / "flows")
        Path(p).write_bytes(b"")  # create empty file

        # Append compressed to empty file - should not raise
        tctx.configure(sa, save_stream_file="+" + p, save_stream_compress=True)
        f = tflow.tflow(resp=True)
        sa.request(f)
        sa.response(f)
        tctx.configure(sa, save_stream_file=None)

        assert len(rd_zstd(p)) == 1
