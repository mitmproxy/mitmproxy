"""Process individual messages from a WebSocket connection."""
import re
from mitmproxy import ctx


def websocket_message(flow):
    # get the latest message
    message = flow.websocket.messages[-1]

    # was the message sent from the client or server?
    if message.from_client:
        ctx.log.info(f"Client sent a message: {message.content!r}")
    else:
        ctx.log.info(f"Server sent a message: {message.content!r}")

    # manipulate the message content
    message.content = re.sub(rb'^Hello', b'HAPPY', message.content)

    if b'FOOBAR' in message.content:
        # kill the message and not send it to the other endpoint
        message.content = ""
