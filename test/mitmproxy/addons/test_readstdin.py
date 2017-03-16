
import io
from mitmproxy.addons import readstdin
from mitmproxy.test import taddons
from mitmproxy.test import tflow
import mitmproxy.io
from unittest import mock


def gen_data(corrupt=False):
    tf = io.BytesIO()
    w = mitmproxy.io.FlowWriter(tf)
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
    tf.seek(0)
    return tf


class mStdin:
    def __init__(self, d):
        self.buffer = d

    def isatty(self):
        return False


@mock.patch('mitmproxy.master.Master.load_flow')
def test_read(m, tmpdir):
    rf = readstdin.ReadStdin()
    with taddons.context() as tctx:
        assert not m.called
        rf.running(stdin=mStdin(gen_data()))
        assert m.called

        rf.running(stdin=mStdin(None))
        assert tctx.master.logs
        tctx.master.clear()

        m.reset_mock()
        assert not m.called
        rf.running(stdin=mStdin(gen_data(corrupt=True)))
        assert m.called
        assert tctx.master.logs
