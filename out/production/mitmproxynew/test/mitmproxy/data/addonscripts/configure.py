import typing

from mitmproxy import exceptions


class OptionAddon:
    def load(self, loader):
        loader.add_option(
            name = "optionaddon",
            typespec = typing.Optional[int],
            default = None,
            help = "Option Addon",
        )

    def configure(self, updates):
        raise exceptions.OptionsError("Options Error")

addons = [
    OptionAddon()
]

