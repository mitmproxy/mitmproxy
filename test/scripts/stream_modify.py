def modify(chunks):
    for prefix, content, suffix in chunks:
        yield prefix, content.replace("foo", "bar"), suffix


def responseheaders(context, flow):
    flow.response.stream = modify
