"""
Inject a WebSocket message into a running connection.

This example shows how to inject a WebSocket message into a running connection.
"""
import asyncio

from mitmproxy import ctx, http


# Simple example: Inject a message as a response to an event

def websocket_message(flow: http.HTTPFlow):
    assert flow.websocket is not None  # make type checker happy
    last_message = flow.websocket.messages[-1]
    if last_message.is_text and "secret" in last_message.text:
        last_message.drop()
        ctx.master.commands.call(
            "inject.websocket",           # Command to invoke
            flow,                         # Flow where we want to inject the message
            last_message.from_client,     # Whether we want to send it to the client
            "ssssssh".encode()            # Contents of the message
        )


# Simple example: Inject a CLOSE message to close the WS connection

def websocket_message(flow: http.HTTPFlow):
    assert flow.websocket is not None  # make type checker happy
    last_message = flow.websocket.messages[-1]
    if last_message.is_text and "close-connection" in last_message.text:
        last_message.drop()
        ctx.master.commands.call(
            "inject.websocket",           # Command to invoke
            flow,                         # Flow that we want to close
            last_message.from_client,     # Whether we want to close the conn to the client
            "Closed by proxy".encode(),   # Reason message to close the conn
            False,                        # Whether we want to inject a TEXT opcode -> sending a message
            True                          # Whether we want to inject a CLOSE opcode -> closing the conn
        )


# Complex example: Schedule a periodic timer

async def inject_async(flow: http.HTTPFlow):
    msg = "hello from mitmproxy! "
    assert flow.websocket is not None  # make type checker happy
    while flow.websocket.timestamp_end is None:
        ctx.master.commands.call(
            "inject.websocket",           # Command to invoke
            flow,                         # Flow where we want to inject the message
            True,                         # Whether we want to send it to the client
            msg.encode()                  # Contents of the message
        )
        await asyncio.sleep(1)
        msg = msg[1:] + msg[:1]


def websocket_start(flow: http.HTTPFlow):
    asyncio.create_task(inject_async(flow))
