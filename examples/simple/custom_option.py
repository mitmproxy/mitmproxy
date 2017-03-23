from mitmproxy import ctx


def load(options):
    ctx.log.info("Registering option 'custom'")
    options.add_option("custom", bool, False, "A custom option")


def configure(options, updated):
    if "custom" in updated:
        ctx.log.info("custom option value: %s" % options.custom)
