"""
This example shows how to inject a WebSocket message to the client.
Every new WebSocket connection will trigger a new asyncio task that
periodically injects a new message to the client.
"""
import asyncio
import mitmproxy.websocket


class InjectWebSocketMessage:

    async def inject(self, flow: mitmproxy.websocket.WebSocketFlow):
        i = 0
        while not flow.ended and not flow.error:
            await asyncio.sleep(5)
            flow.inject_message(flow.client_conn, 'This is the #{} an injected message!'.format(i))
            i += 1

    def websocket_start(self, flow):
        asyncio.get_event_loop().create_task(self.inject(flow))


addons = [InjectWebSocketMessage()]
