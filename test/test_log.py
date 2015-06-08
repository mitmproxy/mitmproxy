import StringIO
from libpathod import log
import netlib.tcp


class DummyIO(StringIO.StringIO):
    def start_log(self, *args, **kwargs):
        pass

    def get_log(self, *args, **kwargs):
        return ""


def test_disconnect():
    outf = DummyIO()
    rw = DummyIO()
    try:
        with log.Log(outf, False, rw, rw) as lg:
            lg("Test")
    except netlib.tcp.NetLibDisconnect:
        pass
    assert "Test" in outf.getvalue()
