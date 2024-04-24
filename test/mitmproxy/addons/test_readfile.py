import asyncio
import io
from unittest import mock

import pytest

import mitmproxy.io
from mitmproxy import exceptions
from mitmproxy.addons import readfile
from mitmproxy.test import taddons
from mitmproxy.test import tflow


@pytest.fixture
def data():
    f = io.BytesIO()

    w = mitmproxy.io.FlowWriter(f)
    flows = [
        tflow.tflow(resp=True),
        tflow.tflow(err=True),
        tflow.ttcpflow(),
        tflow.ttcpflow(err=True),
    ]
    for flow in flows:
        w.add(flow)

    f.seek(0)
    return f


@pytest.fixture
def corrupt_data(data):
    f = io.BytesIO(data.getvalue())
    f.seek(0, io.SEEK_END)
    f.write(b"qibble")
    f.seek(0)
    return f


class TestReadFile:
    def test_configure(self):
        rf = readfile.ReadFile()
        with taddons.context(rf) as tctx:
            tctx.configure(rf, readfile_filter="~q")
            with pytest.raises(Exception, match="Invalid filter expression"):
                tctx.configure(rf, readfile_filter="~~")
            tctx.configure(rf, readfile_filter="")

    async def test_read(self, tmpdir, data, corrupt_data, caplog_async):
        rf = readfile.ReadFile()
        with taddons.context(rf) as tctx:
            assert not rf.reading()

            tf = tmpdir.join("tfile")

            load_called = asyncio.Event()

            async def load_flow(*_, **__):
                load_called.set()

            tctx.master.load_flow = load_flow

            tf.write(data.getvalue())
            tctx.configure(rf, rfile=str(tf), readfile_filter=".*")
            assert not load_called.is_set()
            rf.running()
            await load_called.wait()

            while rf.reading():
                await asyncio.sleep(0)

            tf.write(corrupt_data.getvalue())
            tctx.configure(rf, rfile=str(tf))
            rf.running()
            await caplog_async.await_log("corrupted")

    async def test_corrupt(self, corrupt_data, caplog_async):
        rf = readfile.ReadFile()
        with taddons.context(rf):
            with pytest.raises(exceptions.FlowReadException):
                await rf.load_flows(io.BytesIO(b"qibble"))

            caplog_async.clear()
            with pytest.raises(exceptions.FlowReadException):
                await rf.load_flows(corrupt_data)
            await caplog_async.await_log("file corrupted")

    async def test_nonexistent_file(self, caplog):
        rf = readfile.ReadFile()
        with pytest.raises(exceptions.FlowReadException):
            await rf.load_flows_from_path("nonexistent")
        assert "nonexistent" in caplog.text


class TestReadFileStdin:
    @mock.patch("sys.stdin")
    async def test_stdin(self, stdin, data, corrupt_data):
        rf = readfile.ReadFileStdin()
        with taddons.context(rf):
            with mock.patch("mitmproxy.master.Master.load_flow") as mck:
                stdin.buffer = data
                mck.assert_not_awaited()
                await rf.load_flows(stdin.buffer)
                mck.assert_awaited()

                stdin.buffer = corrupt_data
                with pytest.raises(exceptions.FlowReadException):
                    await rf.load_flows(stdin.buffer)

    async def test_normal(self, tmpdir, data):
        rf = readfile.ReadFileStdin()
        with taddons.context(rf) as tctx:
            tf = tmpdir.join("tfile")
            with mock.patch("mitmproxy.master.Master.load_flow") as mck:
                tf.write(data.getvalue())
                tctx.configure(rf, rfile=str(tf))
                mck.assert_not_awaited()
                rf.running()
                await asyncio.sleep(0)
                mck.assert_awaited()
