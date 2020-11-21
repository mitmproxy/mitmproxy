import asyncio
import traceback
import typing

import mitmproxy.types
from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import io
from mitmproxy.addons.proxyserver import AsyncReply
from mitmproxy.net import server_spec
from mitmproxy.options import Options
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events, layers, server
from mitmproxy.proxy2.context import Context, Server
from mitmproxy.proxy2.layer import CommandGenerator
from mitmproxy.utils import asyncio_utils


class MockServer(layers.http.HttpConnection):
    """
    A mock HTTP "server" that just pretends it received a full HTTP request,
    which is then processed by the proxy core.
    """
    flow: http.HTTPFlow

    def __init__(self, flow: http.HTTPFlow, context: Context):
        super().__init__(context, context.client)
        self.flow = flow

    def _handle_event(self, event: events.Event) -> CommandGenerator[None]:
        if isinstance(event, events.Start):
            yield layers.http.ReceiveHttp(layers.http.RequestHeaders(1, self.flow.request))
            if self.flow.request.raw_content:
                yield layers.http.ReceiveHttp(layers.http.RequestData(1, self.flow.request.raw_content))
            yield layers.http.ReceiveHttp(layers.http.RequestEndOfMessage(1))
        elif isinstance(event, (
                layers.http.ResponseHeaders,
                layers.http.ResponseData,
                layers.http.ResponseEndOfMessage,
                layers.http.ResponseProtocolError,
        )):
            pass
        else:
            ctx.log(f"Unexpected event during replay: {events}")


class ReplayHandler(server.ConnectionHandler):
    def __init__(self, flow: http.HTTPFlow, options: Options) -> None:
        client = flow.client_conn.copy()

        context = Context(client, options)
        context.server = Server(
            (flow.request.host, flow.request.port)
        )
        context.server.tls = flow.request.scheme == "https"
        if options.mode.startswith("upstream:"):
            context.server.via = server_spec.parse_with_mode(options.mode)[1]

        super().__init__(context)

        self.layer = layers.HttpLayer(context, HTTPMode.transparent)
        self.layer.connections[client] = MockServer(flow, context.fork())
        self.flow = flow
        self.done = asyncio.Event()

    async def replay(self) -> None:
        self.server_event(events.Start())
        await self.done.wait()

    def log(self, message: str, level: str = "info") -> None:
        ctx.log(f"[replay] {message}", level)

    async def handle_hook(self, hook: commands.Hook) -> None:
        data, = hook.as_tuple()
        data.reply = AsyncReply(data)
        await ctx.master.addons.handle_lifecycle(hook.name, data)
        await data.reply.done.wait()
        if isinstance(hook, (layers.http.HttpResponseHook, layers.http.HttpErrorHook)):
            if self.transports:
                # close server connections
                for x in self.transports.values():
                    x.handler.cancel()
                await asyncio.wait([x.handler for x in self.transports.values()])
            # signal completion
            self.done.set()


class ClientPlayback:
    playback_task: typing.Optional[asyncio.Task]
    inflight: typing.Optional[http.HTTPFlow]
    queue: asyncio.Queue
    options: Options

    def __init__(self):
        self.queue = asyncio.Queue()
        self.inflight = None
        self.task = None

    def running(self):
        self.playback_task = asyncio_utils.create_task(
            self.playback(),
            name="client playback"
        )
        self.options = ctx.options

    def done(self):
        self.playback_task.cancel()

    async def playback(self):
        while True:
            self.inflight = await self.queue.get()
            try:
                h = ReplayHandler(self.inflight, self.options)
                await h.replay()
            except Exception:
                ctx.log(f"Client replay has crashed!\n{traceback.format_exc()}", "error")
            self.inflight = None

    def check(self, f: flow.Flow) -> typing.Optional[str]:
        if f.live:
            return "Can't replay live flow."
        if f.intercepted:
            return "Can't replay intercepted flow."
        if isinstance(f, http.HTTPFlow):
            if not f.request:
                return "Can't replay flow with missing request."
            if f.request.raw_content is None:
                return "Can't replay flow with missing content."
        else:
            return "Can only replay HTTP flows."

    def load(self, loader):
        loader.add_option(
            "client_replay", typing.Sequence[str], [],
            "Replay client requests from a saved file."
        )

    def configure(self, updated):
        if "client_replay" in updated and ctx.options.client_replay:
            try:
                flows = io.read_flows_from_paths(ctx.options.client_replay)
            except exceptions.FlowReadException as e:
                raise exceptions.OptionsError(str(e))
            self.start_replay(flows)

    @command.command("replay.client.count")
    def count(self) -> int:
        """
            Approximate number of flows queued for replay.
        """
        return self.queue.qsize() + int(bool(self.inflight))

    @command.command("replay.client.stop")
    def stop_replay(self) -> None:
        """
            Clear the replay queue.
        """
        updated = []
        while True:
            try:
                f = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            else:
                f.revert()
                updated.append(f)

        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Client replay queue cleared.")

    @command.command("replay.client")
    def start_replay(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Add flows to the replay queue, skipping flows that can't be replayed.
        """
        updated: typing.List[http.HTTPFlow] = []
        for f in flows:
            err = self.check(f)
            if err:
                ctx.log.warn(err)
                continue

            http_flow = typing.cast(http.HTTPFlow, f)

            # Prepare the flow for replay
            http_flow.backup()
            http_flow.is_replay = "request"
            http_flow.response = None
            http_flow.error = None
            self.queue.put_nowait(http_flow)
            updated.append(http_flow)
        ctx.master.addons.trigger("update", updated)

    @command.command("replay.client.file")
    def load_file(self, path: mitmproxy.types.Path) -> None:
        """
            Load flows from file, and add them to the replay queue.
        """
        try:
            flows = io.read_flows_from_paths([path])
        except exceptions.FlowReadException as e:
            raise exceptions.CommandError(str(e))
        self.start_replay(flows)
