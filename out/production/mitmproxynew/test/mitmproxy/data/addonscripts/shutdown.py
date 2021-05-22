from mitmproxy import ctx


def running():
    ctx.master.shutdown()