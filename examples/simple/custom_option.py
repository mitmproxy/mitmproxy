from mitmproxy import ctx


def start(options):
    ctx.log.info("Registering option 'custom'")
    options.add_option("custom", str, "default", "A custom option")


def configure(options, updated):
    ctx.log.info("custom option value: %s" % options.custom)
