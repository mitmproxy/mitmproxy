import io
from pathlib import Path

import pytest
from hypothesis import example
from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy import exceptions
from mitmproxy import version
from mitmproxy.io import FlowReader
from mitmproxy.io import tnetstring

here = Path(__file__).parent.parent / "data"


class TestFlowReader:
    @given(binary())
    @example(b"51:11:12345678901#4:this,8:true!0:~,4:true!0:]4:\\x00,~}")
    @example(b"0:")
    def test_fuzz(self, data):
        f = io.BytesIO(data)
        reader = FlowReader(f)
        try:
            for _ in reader.stream():
                pass
        except exceptions.FlowReadException:
            pass  # should never raise anything else.

    @pytest.mark.parametrize(
        "file", [pytest.param(x, id=x.stem) for x in here.glob("har_files/*.har")]
    )
    def test_har(self, file):
        with open(file, "rb") as f:
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
            weird_flow = tnetstring.dumps(
                {"type": "unknown", "version": version.FLOW_FORMAT_VERSION}
            )
            for _ in FlowReader(io.BytesIO(weird_flow)).stream():
                pass

    def test_cannot_migrate(self):
        with pytest.raises(
            exceptions.FlowReadException,
            match="cannot read files with flow format version 0",
        ):
            for _ in FlowReader(io.BytesIO(b"14:7:version;1:0#}")).stream():
                pass
