import mock
from mitmproxy import controller


class TestMaster:

    def test_default_handler(self):
        m = controller.Master(None)
        msg = mock.MagicMock()
        m.handle("type", msg)
        assert msg.reply.call_count == 1
