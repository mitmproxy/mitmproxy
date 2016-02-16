import StringIO
from pathod import log
from netlib.exceptions import TcpDisconnect
import netlib.tcp


class DummyIO(StringIO.StringIO):

    def start_log(self, *args, **kwargs):
        pass

    def get_log(self, *args, **kwargs):
        return ""


def test_disconnect():
    outf = DummyIO()
    rw = DummyIO()
    l = log.ConnectionLogger(outf, False, rw, rw)
    try:
        with l.ctx() as lg:
            lg("Test")
    except TcpDisconnect:
        pass
    assert "Test" in outf.getvalue()
