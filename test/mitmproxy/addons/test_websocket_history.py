import gc
import weakref

import pytest

from mitmproxy import exceptions
from mitmproxy.addons import websocket_history
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.websocket import WebSocketData


def test_defaults():
    addon = websocket_history.WebSocketHistory()
    with taddons.context(addon) as tctx:
        live = tflow.tflow(ws=WebSocketData())
        addon.websocket_start(live)
        assert not live.websocket.store_messages

        # Saved flows keep their history and never block configuration changes.
        saved = tflow.twebsocketflow().copy()
        addon.websocket_start(saved)
        assert saved.websocket.store_messages
        assert len(saved.websocket.messages) == 3

        # Unrelated settings and turning retention off remain possible.
        tctx.options.update(server=False, keep_websocket_messages=False)
        with pytest.raises(exceptions.OptionsError, match="Close these connections"):
            tctx.options.update(keep_websocket_messages=True)
        assert not tctx.options.keep_websocket_messages

        # Holding a finished flow must not block new recording sessions.
        live.live = False
        tctx.options.update(keep_websocket_messages=True)
        recorded = tflow.tflow(ws=WebSocketData())
        addon.websocket_start(recorded)
        assert recorded.websocket.store_messages


def test_does_not_own_flows():
    addon = websocket_history.WebSocketHistory()
    with taddons.context(addon) as tctx:
        flow = tflow.tflow(ws=WebSocketData())
        addon.websocket_start(flow)
        ref = weakref.ref(flow)
        del flow
        gc.collect()
        assert ref() is None
        tctx.options.update(keep_websocket_messages=True)
