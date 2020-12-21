from mitmproxy.net import websocket


def test_check_handshake():
    assert not websocket.check_handshake({
        "connection": "upgrade",
        "upgrade": "webFOOsocket",
        "sec-websocket-key": "foo",
    })
    assert websocket.check_handshake({
        "connection": "upgrade",
        "upgrade": "websocket",
        "sec-websocket-key": "foo",
    })
    assert websocket.check_handshake({
        "connection": "upgrade",
        "upgrade": "websocket",
        "sec-websocket-accept": "bar",
    })


def test_get_extensions():
    assert websocket.get_extensions({}) is None
    assert websocket.get_extensions({"sec-websocket-extensions": "foo"}) == "foo"


def test_get_protocol():
    assert websocket.get_protocol({}) is None
    assert websocket.get_protocol({"sec-websocket-protocol": "foo"}) == "foo"


def test_get_client_key():
    assert websocket.get_client_key({}) is None
    assert websocket.get_client_key({"sec-websocket-key": "foo"}) == "foo"


def test_get_server_accept():
    assert websocket.get_server_accept({}) is None
    assert websocket.get_server_accept({"sec-websocket-accept": "foo"}) == "foo"
