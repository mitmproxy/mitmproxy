"""Process individual messages from a WebSocket connection."""
import re
from mitmproxy import ctx


def websocket_message(flow):
    # get the latest message
    message = flow.messages[-1]

    # was the message sent from the client or server?
    if message.from_client:
        ctx.log.info(f"Client sent a message: {message.content}")
    else:
        ctx.log.info(f"Server sent a message: {message.content}")

    # manipulate the message content
    message.content = re.sub(r'^Hello', 'HAPPY', message.content)

    if 'FOOBAR' in message.content:
        # kill the message and not send it to the other endpoint
        message.kill()
