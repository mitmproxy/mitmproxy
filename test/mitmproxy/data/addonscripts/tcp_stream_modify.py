from mitmproxy import ctx

def tcp_message():
    message = ctx.flow.messages[-1]
    if not message.from_client:
        message.content = message.content.replace("foo", "bar")
