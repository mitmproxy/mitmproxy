from mitmproxy import ctx


class KeepServing:
    def load(self, loader):
        loader.add_option(
            "keepserving", bool, False,
            """
            Continue serving after client playback, server playback or file
            read. This option is ignored by interactive tools, which always keep
            serving.
            """
        )

    def event_processing_complete(self):
        if not ctx.master.options.keepserving:
            ctx.master.shutdown()
