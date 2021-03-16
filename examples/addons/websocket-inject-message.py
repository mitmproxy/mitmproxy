"""
Inject a WebSocket message into a running connection.

This example shows how to inject a WebSocket message into a running connection.
"""
import asyncio

from mitmproxy import ctx, http


# Simple example: Inject a message as a response to an event

def websocket_message(flow):
    last_message = flow.websocket.messages[-1]
    if b"secret" in last_message.content:
        last_message.kill()
        ctx.master.commands.call("inject.websocket", flow, last_message.from_client, "ssssssh")


# Complex example: Schedule a periodic timer

async def inject_async(flow: http.HTTPFlow):
    msg = "hello from mitmproxy! "
    assert flow.websocket  # make type checker happy
    while flow.websocket.timestamp_end is None:
        ctx.master.commands.call("inject.websocket", flow, True, msg)
        await asyncio.sleep(1)
        msg = msg[1:] + msg[:1]


def websocket_start(flow: http.HTTPFlow):
    asyncio.create_task(inject_async(flow))
