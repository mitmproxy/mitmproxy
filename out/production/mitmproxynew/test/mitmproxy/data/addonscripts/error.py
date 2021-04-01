from mitmproxy import ctx


def running():
    ctx.log.info("error running")


def request(flow):
    raise ValueError("Error!")
