import os
import mitmproxy
from mitmproxy import ctx


CONF_DIR = "~/.mitmproxy"
if not os.path.isdir(os.path.expanduser(CONF_DIR)):
    CONF_DIR = os.getenv('XDG_CONFIG_HOME', '~/.config') + '/mitmproxy'

class CheckCA:
    def __init__(self):
        self.failed = False

    def configure(self, updated):
        has_ca = (
            mitmproxy.ctx.master.server and
            mitmproxy.ctx.master.server.config and
            mitmproxy.ctx.master.server.config.certstore and
            mitmproxy.ctx.master.server.config.certstore.default_ca
        )
        if has_ca:
            self.failed = mitmproxy.ctx.master.server.config.certstore.default_ca.has_expired()
            if self.failed:
                ctx.log.warn(
                    "The mitmproxy certificate authority has expired!\n"
                    "Please delete all CA-related files in your " + CONF_DIR + " folder.\n"
                    "The CA will be regenerated automatically after restarting mitmproxy.\n"
                    "Then make sure all your clients have the new CA installed.",
                )
