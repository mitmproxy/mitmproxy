def modify(chunks):
    for chunk in chunks:
        yield chunk.replace("foo", "bar")


def responseheaders(context, flow):
    flow.response.stream = modify
