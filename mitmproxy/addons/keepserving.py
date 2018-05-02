import asyncio
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

    def keepgoing(self) -> bool:
        checks = [
            "readfile.reading",
            "replay.client.count",
            "replay.server.count",
        ]
        return any([ctx.master.commands.call(c) for c in checks])

    def shutdown(self):  # pragma: no cover
        ctx.master.shutdown()

    async def watch(self):
        while True:
            await asyncio.sleep(0.1)
            if not self.keepgoing():
                self.shutdown()

    def running(self):
        opts = [
            ctx.options.client_replay,
            ctx.options.server_replay,
            ctx.options.rfile,
        ]
        if any(opts) and not ctx.options.keepserving:
            asyncio.get_event_loop().create_task(self.watch())
