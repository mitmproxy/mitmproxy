"""React to configuration changes."""
import typing

from mitmproxy import ctx
from mitmproxy import exceptions


class AddHeader:
    def load(self, loader):
        loader.add_option(
            name = "addheader",
            typespec = typing.Optional[int],
            default = None,
            help = "Add a header to responses",
        )

    def configure(self, updates):
        if "addheader" in updates:
            if ctx.options.addheader is not None and ctx.options.addheader > 100:
                raise exceptions.OptionsError("addheader must be <= 100")

    def response(self, flow):
        if ctx.options.addheader is not None:
            flow.response.headers["addheader"] = str(ctx.options.addheader)


addons = [
    AddHeader()
]
