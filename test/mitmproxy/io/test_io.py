import io

import pytest
from hypothesis import example, given
from hypothesis.strategies import binary

from mitmproxy import exceptions, version
from mitmproxy.io import FlowReader, tnetstring


class TestFlowReader:
    @given(binary())
    @example(b'51:11:12345678901#4:this,8:true!0:~,4:true!0:]4:\\x00,~}')
    def test_fuzz(self, data):
        f = io.BytesIO(data)
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
            weird_flow = tnetstring.dumps({"type": "unknown", "version": version.FLOW_FORMAT_VERSION})
            for _ in FlowReader(io.BytesIO(weird_flow)).stream():
                pass

    def test_cannot_migrate(self):
        with pytest.raises(exceptions.FlowReadException, match="cannot read files with flow format version 0"):
            for _ in FlowReader(io.BytesIO(b"14:7:version;1:0#}")).stream():
                pass
