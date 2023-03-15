import logging


def modify(chunks):
    for chunk in chunks:
        yield chunk.replace(b"foo", b"bar")


def running():
    logging.info("stream_modify running")


def responseheaders(flow):
    flow.response.stream = modify
