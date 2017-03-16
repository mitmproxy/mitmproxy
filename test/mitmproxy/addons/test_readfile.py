from mitmproxy.addons import readfile
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy import io
from mitmproxy import exceptions
from unittest import mock

import pytest


def write_data(path, corrupt=False):
    with open(path, "wb") as tf:
        w = io.FlowWriter(tf)
        for i in range(3):
            f = tflow.tflow(resp=True)
            w.add(f)
        for i in range(3):
            f = tflow.tflow(err=True)
            w.add(f)
        f = tflow.ttcpflow()
        w.add(f)
        f = tflow.ttcpflow(err=True)
        w.add(f)
        if corrupt:
            tf.write(b"flibble")


@mock.patch('mitmproxy.master.Master.load_flow')
def test_configure(mck, tmpdir):

    rf = readfile.ReadFile()
    with taddons.context() as tctx:
        tf = str(tmpdir.join("tfile"))
        write_data(tf)
        tctx.configure(rf, rfile=str(tf))
        assert not mck.called
        rf.running()
        assert mck.called

        write_data(tf, corrupt=True)
        tctx.configure(rf, rfile=str(tf))
        with pytest.raises(exceptions.OptionsError):
            rf.running()


@mock.patch('mitmproxy.master.Master.load_flow')
def test_corruption(mck, tmpdir):

    rf = readfile.ReadFile()
    with taddons.context() as tctx:
        with pytest.raises(exceptions.FlowReadException):
            rf.load_flows_file("nonexistent")
        assert not mck.called
        assert len(tctx.master.logs) == 1

        tfc = str(tmpdir.join("tfile"))
        write_data(tfc, corrupt=True)

        with pytest.raises(exceptions.FlowReadException):
            rf.load_flows_file(tfc)
        assert mck.called
        assert len(tctx.master.logs) == 2
