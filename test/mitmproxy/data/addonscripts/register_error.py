class ErrorDuringLoadAddon:
    def load(self, loader):
        raise ValueError("Something went wrong during addon load")


addons = [ErrorDuringLoadAddon()]
