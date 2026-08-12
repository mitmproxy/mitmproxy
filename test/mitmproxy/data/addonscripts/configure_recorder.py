class ConfigureRecorder:
    """
    Records every `updated` set passed to `configure()`, so tests can check
    whether `configure()` was actually invoked after an option change.
    """

    call_log = []

    def load(self, loader):
        loader.add_option(
            name="recorder_option",
            typespec=str,
            default="default",
            help="A custom option for testing that configure() gets called.",
        )

    def configure(self, updated):
        self.call_log.append(set(updated))


addons = [ConfigureRecorder()]
