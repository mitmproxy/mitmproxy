from mitmproxy import ctx


class KeepServing:
    def event_processing_complete(self):
        if not ctx.master.options.keepserving:
            ctx.master.shutdown()
