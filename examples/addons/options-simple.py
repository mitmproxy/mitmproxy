"""
Add a new mitmproxy option.

Usage:

    mitmproxy -s options-simple.py --set addheader true
"""
from mitmproxy import ctx


class AddHeader:
    def __init__(self):
        self.num = 0

    def load(self, loader):
        loader.add_option(
            name = "addheader",
            typespec = bool,
            default = False,
            help = "Add a count header to responses",
        )

    def response(self, flow):
        if ctx.options.addheader:
            self.num = self.num + 1
            flow.response.headers["count"] = str(self.num)


addons = [
    AddHeader()
]
