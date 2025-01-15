"""
Inject a WebSocket message into a running connection.

This example shows how to inject a WebSocket message into a running connection.
"""

import asyncio

from mitmproxy import ctx
from mitmproxy import http

# Simple example: Inject a message as a response to an event


def websocket_message(flow: http.HTTPFlow):
    assert flow.websocket is not None  # make type checker happy
    last_message = flow.websocket.messages[-1]
    if last_message.is_text and "secret" in last_message.text:
        last_message.drop()
        ctx.master.commands.call(
            "inject.websocket", flow, last_message.from_client, b"ssssssh"
        )


# Complex example: Schedule a periodic timer


async def inject_async(flow: http.HTTPFlow):
    msg = "hello from mitmproxy! "
    assert flow.websocket is not None  # make type checker happy
    while flow.websocket.timestamp_end is None:
        ctx.master.commands.call("inject.websocket", flow, True, msg.encode())
        await asyncio.sleep(1)
        msg = msg[1:] + msg[:1]


tasks = set()


def websocket_start(flow: http.HTTPFlow):
    # we need to hold a reference to the task, otherwise it will be garbage collected.
    t = asyncio.create_task(inject_async(flow))
    tasks.add(t)
    t.add_done_callback(tasks.remove)
