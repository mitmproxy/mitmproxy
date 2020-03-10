import typing

from mitmproxy import ctx
from mitmproxy import exceptions


class TestHeader:
    def load(self, loader):
        loader.add_option(
            name = "testheader",
            typespec = typing.Optional[int],
            default = None,
            help = "test header",
        )

    def configure(self, updates):
        raise exceptions.OptionsError("Options Error")

    def response(self, flow):
        if ctx.options.testheader is not None:
            flow.response.headers["testheader"] = str(ctx.options.testheader)


addons = [
    TestHeader()
]

