from __future__ import absolute_import, print_function, division

from mitmproxy import ctx


class AntiCache:
    def __init__(self):
        self.enabled = False

    def configure(self, options):
        self.enabled = options.anticache

    def request(self):
        if self.enabled:
            ctx.flow.request.anticache()
