import bz2
import gzip
import io
import lzma
from pathlib import Path

import pytest
from hypothesis import example
from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy import exceptions
from mitmproxy import version
from mitmproxy.io import FlowReader
from mitmproxy.io import FlowWriter
from mitmproxy.io import open_flow_file
from mitmproxy.io import read_flows_from_paths
from mitmproxy.io import tnetstring
from mitmproxy.test import tflow

here = Path(__file__).parent.parent / "data"


class TestFlowReader:
    @given(binary())
    @example(b"51:11:12345678901#4:this,8:true!0:~,4:true!0:]4:\\x00,~}")
    @example(b"0:")
    @example(b"0:~")
    def test_fuzz(self, data):
        f = io.BytesIO(data)
        reader = FlowReader(f)
        try:
            for _ in reader.stream():
                pass
        except exceptions.FlowReadException:
            pass  # should never raise anything else.

    @pytest.mark.parametrize(
        "file", [pytest.param(x, id=x.stem) for x in here.glob("har_files/*.har")]
    )
    def test_har(self, file):
        with open(file, "rb") as f:
            reader = FlowReader(f)
            try:
                for _ in reader.stream():
                    pass
            except exceptions.FlowReadException:
                pass  # should never raise anything else.

    def test_empty(self):
        assert list(FlowReader(io.BytesIO(b"")).stream()) == []

    def test_unknown_type(self):
        with pytest.raises(exceptions.FlowReadException, match="Unknown flow type"):
            weird_flow = tnetstring.dumps(
                {"type": "unknown", "version": version.FLOW_FORMAT_VERSION}
            )
            for _ in FlowReader(io.BytesIO(weird_flow)).stream():
                pass

    def test_cannot_migrate(self):
        with pytest.raises(
            exceptions.FlowReadException,
            match="cannot read files with flow format version 0",
        ):
            for _ in FlowReader(io.BytesIO(b"14:7:version;1:0#}")).stream():
                pass


def _write_flow_to_file(path, compress_open=None):
    """Helper to write a test flow to a file, optionally compressed."""
    f = tflow.tflow(resp=True)
    if compress_open:
        with compress_open(str(path), "wb") as fo:
            FlowWriter(fo).add(f)
    else:
        with open(str(path), "wb") as fo:
            FlowWriter(fo).add(f)
    return f


class TestOpenFlowFile:
    def test_uncompressed(self, tmp_path):
        p = tmp_path / "flows"
        _write_flow_to_file(p)
        with open_flow_file(str(p)) as f:
            flows = list(FlowReader(f).stream())
        assert len(flows) == 1
        assert flows[0].response

    def test_gzip(self, tmp_path):
        p = tmp_path / "flows.bin"
        _write_flow_to_file(p, gzip.open)
        with open_flow_file(str(p)) as f:
            flows = list(FlowReader(f).stream())
        assert len(flows) == 1
        assert flows[0].response

    def test_bz2(self, tmp_path):
        p = tmp_path / "flows.bin"
        _write_flow_to_file(p, bz2.open)
        with open_flow_file(str(p)) as f:
            flows = list(FlowReader(f).stream())
        assert len(flows) == 1
        assert flows[0].response

    def test_xz(self, tmp_path):
        p = tmp_path / "flows.bin"
        _write_flow_to_file(p, lzma.open)
        with open_flow_file(str(p)) as f:
            flows = list(FlowReader(f).stream())
        assert len(flows) == 1
        assert flows[0].response

    def test_concatenated_gzip(self, tmp_path):
        p = tmp_path / "flows.bin"
        _write_flow_to_file(p, gzip.open)
        # Append a second gzip member
        f2 = tflow.tflow(resp=True)
        with gzip.open(str(p), "ab") as fo:
            FlowWriter(fo).add(f2)
        with open_flow_file(str(p)) as f:
            flows = list(FlowReader(f).stream())
        assert len(flows) == 2


class TestReadFlowsFromPathsCompressed:
    def test_gzip(self, tmp_path):
        p = tmp_path / "flows.gz"
        _write_flow_to_file(p, gzip.open)
        flows = read_flows_from_paths([str(p)])
        assert len(flows) == 1

    def test_bz2(self, tmp_path):
        p = tmp_path / "flows.bz2"
        _write_flow_to_file(p, bz2.open)
        flows = read_flows_from_paths([str(p)])
        assert len(flows) == 1

    def test_xz(self, tmp_path):
        p = tmp_path / "flows.xz"
        _write_flow_to_file(p, lzma.open)
        flows = read_flows_from_paths([str(p)])
        assert len(flows) == 1


class TestCorruptCompressedFiles:
    def test_corrupt_gzip(self, tmp_path):
        # Valid gzip magic but corrupt data
        p = tmp_path / "corrupt.bin"
        p.write_bytes(b"\x1f\x8b" + b"\x00" * 20)
        with pytest.raises(exceptions.FlowReadException):
            with open_flow_file(str(p)) as f:
                list(FlowReader(f).stream())

    def test_corrupt_bz2(self, tmp_path):
        p = tmp_path / "corrupt.bin"
        p.write_bytes(b"BZh" + b"\x00" * 20)
        with pytest.raises(exceptions.FlowReadException):
            with open_flow_file(str(p)) as f:
                list(FlowReader(f).stream())

    def test_corrupt_xz(self, tmp_path):
        p = tmp_path / "corrupt.bin"
        p.write_bytes(b"\xfd7zXZ\x00" + b"\x00" * 20)
        with pytest.raises(exceptions.FlowReadException):
            with open_flow_file(str(p)) as f:
                list(FlowReader(f).stream())

    def test_corrupt_gzip_via_read_flows_from_paths(self, tmp_path):
        p = tmp_path / "corrupt.bin"
        p.write_bytes(b"\x1f\x8b" + b"\x00" * 20)
        with pytest.raises(exceptions.FlowReadException):
            read_flows_from_paths([str(p)])
