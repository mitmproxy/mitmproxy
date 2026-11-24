class BadOptionAddon:
    def load(self, loader):
        loader.add_option(
            name="badoption",
            typespec=int,
            default="not_an_int",
            help="This option has an invalid default",
        )


addons = [BadOptionAddon()]
