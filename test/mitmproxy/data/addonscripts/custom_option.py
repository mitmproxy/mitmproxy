from typing import Optional


class CustomOptionAddon:
    def load(self, loader):
        loader.add_option(
            name="custom_addon_option",
            typespec=Optional[int],
            default=None,
            help="A custom option registered by an addon.",
        )


addons = [CustomOptionAddon()]
