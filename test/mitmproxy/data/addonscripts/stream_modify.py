from mitmproxy import ctx

def modify(chunks):
    for chunk in chunks:
        yield chunk.replace("foo", "bar")


def responseheaders():
    ctx.flow.response.stream = modify
