from unittest import mock

import pytest

from mitmproxy import exceptions
from mitmproxy.io import FlowReader


class TestFlowReader:
    @mock.patch("mitmproxy.io.tnetstring.load")
    @mock.patch("mitmproxy.io.compat.migrate_flow")
    def test_stream_with_exception(self, mock1, mock2):
        with open("./abc", "rb") as fp:
            reader = FlowReader(fp)
            mock2.side_effect = ValueError()
            with pytest.raises(exceptions.FlowReadException, match="Invalid data format."):
                for i in reader.stream():
                    pass
            mock2.side_effect = None
            mock1.side_effect = ValueError("TestException")
            with pytest.raises(exceptions.FlowReadException, match="TestException"):
                for i in reader.stream():
                    pass
            mock1.side_effect = None
            mock1.return_value = {"type": "test_type"}
            with pytest.raises(exceptions.FlowReadException, match="Unknown flow type: test_type"):
                for i in reader.stream():
                    pass
