from mitmproxy import ctx


def load(loader):
    ctx.log.info("error load")


def request(flow):
    raise ValueError("Error!")
