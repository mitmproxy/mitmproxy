import re
from mitmproxy import ctx


def websocket_message(flow):
    # get the latest message
    message = flow.messages[-1]

    # simply print the content of the message
    ctx.log.info(message.content)

    # manipulate the message content
    message.content = re.sub(r'^Hello', 'HAPPY', message.content)
