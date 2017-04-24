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
        tflow.ttcpflow(err=True)
    ]
    for flow in flows:
        w.add(flow)

    f.seek(0)
    return f


@pytest.fixture
def corrupt_data():
    f = data()
    f.seek(0, io.SEEK_END)
    f.write(b"qibble")
    f.seek(0)
    return f


@mock.patch('mitmproxy.master.Master.load_flow')
def test_configure(mck, tmpdir, data, corrupt_data):
    rf = readfile.ReadFile()
    with taddons.context() as tctx:
        tf = tmpdir.join("tfile")

        tf.write(data.getvalue())
        tctx.configure(rf, rfile=str(tf))
        assert not mck.called
        rf.running()
        assert mck.called

        tf.write(corrupt_data.getvalue())
        tctx.configure(rf, rfile=str(tf))
        with pytest.raises(exceptions.OptionsError):
            rf.running()


@mock.patch('mitmproxy.master.Master.load_flow')
@mock.patch('sys.stdin')
def test_configure_stdin(stdin, load_flow, data, corrupt_data):
    rf = readfile.ReadFile()
    with taddons.context() as tctx:
        stdin.buffer = data
        tctx.configure(rf, rfile="-")
        assert not load_flow.called
        rf.running()
        assert load_flow.called

        stdin.buffer = corrupt_data
        tctx.configure(rf, rfile="-")
        with pytest.raises(exceptions.OptionsError):
            rf.running()


@mock.patch('mitmproxy.master.Master.load_flow')
def test_corrupt(mck, corrupt_data):
    rf = readfile.ReadFile()
    with taddons.context() as tctx:
        with pytest.raises(exceptions.FlowReadException):
            rf.load_flows(io.BytesIO(b"qibble"))
        assert not mck.called
        assert len(tctx.master.logs) == 1

        with pytest.raises(exceptions.FlowReadException):
            rf.load_flows(corrupt_data)
        assert mck.called
        assert len(tctx.master.logs) == 2


def test_nonexisting_file():
    rf = readfile.ReadFile()
    with taddons.context() as tctx:
        with pytest.raises(exceptions.FlowReadException):
            rf.load_flows_from_path("nonexistent")
        assert len(tctx.master.logs) == 1
