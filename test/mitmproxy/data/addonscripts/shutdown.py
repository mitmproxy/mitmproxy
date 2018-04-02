from mitmproxy import ctx


def tick():
    ctx.master.shutdown()
