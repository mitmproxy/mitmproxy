def modify(chunks):
    for chunk in chunks:
        yield chunk.replace(b"foo", b"bar")


def responseheaders(context, flow):
    flow.response.stream = modify
