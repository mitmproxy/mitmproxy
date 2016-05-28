from pathod import log
from netlib.exceptions import TcpDisconnect

from io import BytesIO


class DummyIO(BytesIO):

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
            lg(b"Test")
    except TcpDisconnect:
        pass
    assert b"Test" in outf.getvalue()
