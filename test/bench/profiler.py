import cProfile
from mitmproxy import ctx


class Profile:
    """
        A simple profiler addon.
    """
    def __init__(self):
        self.pr = cProfile.Profile()

    def load(self, loader):
        loader.add_option(
            "profile_path",
            str,
            "/tmp/profile",
            "Destination for the run profile, saved at exit"
        )
        self.pr.enable()

    def done(self):
        self.pr.dump_stats(ctx.options.profile_path)


addons = [Profile()]