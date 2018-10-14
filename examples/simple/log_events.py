from mitmproxy import ctx


def load(l):
    ctx.log.info("This is some informative text.")
    ctx.log.warn("This is a warning.")
    ctx.log.error("This is an error.")
