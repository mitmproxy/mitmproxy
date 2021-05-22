from mitmproxy import ctx

def modify(chunks):
    for chunk in chunks:
        yield chunk.replace(b"foo", b"bar")


def running():
    ctx.log.info("stream_modify running")


def responseheaders(flow):
    flow.response.stream = modify
