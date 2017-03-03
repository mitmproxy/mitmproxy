import pytest

from mitmproxy import eventsequence
from mitmproxy.test import tflow


@pytest.mark.parametrize("resp, err", [
    (False, False),
    (True, False),
    (False, True),
    (True, True),
])
def test_http_flow(resp, err):
    f = tflow.tflow(resp=resp, err=err)
    i = eventsequence.iterate(f)
    assert next(i) == ("requestheaders", f)
    assert next(i) == ("request", f)
    if resp:
        assert next(i) == ("responseheaders", f)
        assert next(i) == ("response", f)
    if err:
        assert next(i) == ("error", f)


@pytest.mark.parametrize("err", [False, True])
def test_websocket_flow(err):
    f = tflow.twebsocketflow(err=err)
    i = eventsequence.iterate(f)
    assert next(i) == ("websocket_start", f)
    assert len(f.messages) == 0
    assert next(i) == ("websocket_message", f)
    assert len(f.messages) == 1
    assert next(i) == ("websocket_message", f)
    assert len(f.messages) == 2
    assert next(i) == ("websocket_message", f)
    assert len(f.messages) == 3
    if err:
        assert next(i) == ("websocket_error", f)
    assert next(i) == ("websocket_end", f)


@pytest.mark.parametrize("err", [False, True])
def test_tcp_flow(err):
    f = tflow.ttcpflow(err=err)
    i = eventsequence.iterate(f)
    assert next(i) == ("tcp_start", f)
    assert len(f.messages) == 0
    assert next(i) == ("tcp_message", f)
    assert len(f.messages) == 1
    assert next(i) == ("tcp_message", f)
    assert len(f.messages) == 2
    if err:
        assert next(i) == ("tcp_error", f)
    assert next(i) == ("tcp_end", f)


def test_invalid():
    with pytest.raises(TypeError):
        next(eventsequence.iterate(42))
