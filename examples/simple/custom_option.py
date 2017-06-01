from mitmproxy import ctx


def load(l):
    ctx.log.info("Registering option 'custom'")
    l.add_option("custom", bool, False, "A custom option")


def configure(updated):
    if "custom" in updated:
        ctx.log.info("custom option value: %s" % ctx.options.custom)
