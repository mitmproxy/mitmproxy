def tcp_message(ctx, flow):
    message = flow.messages[-1]
    if not message.from_client:
        message.content = message.content.replace("foo", "bar")
