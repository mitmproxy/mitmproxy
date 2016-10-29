from mitmproxy import ctx


def start():
    ctx.log.info("This is some informative text.")
    ctx.log.error("This is an error.")
