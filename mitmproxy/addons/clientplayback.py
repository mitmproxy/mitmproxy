from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from types import TracebackType
from typing import cast
from typing import Literal

import mitmproxy.types
from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import io
from mitmproxy.connection import ConnectionState
from mitmproxy.connection import Server
from mitmproxy.hooks import UpdateHook
from mitmproxy.log import ALERT
from mitmproxy.options import Options
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layers
from mitmproxy.proxy import server
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layer import CommandGenerator
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.mode_specs import UpstreamMode
from mitmproxy.utils import asyncio_utils

logger = logging.getLogger(__name__)


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
            content = self.flow.request.raw_content
            self.flow.request.timestamp_start = self.flow.request.timestamp_end = (
                time.time()
            )
            yield layers.http.ReceiveHttp(
                layers.http.RequestHeaders(
                    1,
                    self.flow.request,
                    end_stream=not (content or self.flow.request.trailers),
                    replay_flow=self.flow,
                )
            )
            if content:
                yield layers.http.ReceiveHttp(layers.http.RequestData(1, content))
            if self.flow.request.trailers:  # pragma: no cover
                # TODO: Cover this once we support HTTP/1 trailers.
                yield layers.http.ReceiveHttp(
                    layers.http.RequestTrailers(1, self.flow.request.trailers)
                )
            yield layers.http.ReceiveHttp(layers.http.RequestEndOfMessage(1))
        elif isinstance(
            event,
            (
                layers.http.ResponseHeaders,
                layers.http.ResponseData,
                layers.http.ResponseTrailers,
                layers.http.ResponseEndOfMessage,
                layers.http.ResponseProtocolError,
            ),
        ):
            pass
        else:  # pragma: no cover
            logger.warning(f"Unexpected event during replay: {event}")


class ReplayHandler(server.ConnectionHandler):
    layer: layers.HttpLayer

    def __init__(self, flow: http.HTTPFlow, options: Options) -> None:
        client = flow.client_conn.copy()
        client.state = ConnectionState.OPEN

        context = Context(client, options)
        context.server = Server(address=(flow.request.host, flow.request.port))
        if flow.request.scheme == "https":
            context.server.tls = True
            context.server.sni = flow.request.pretty_host
        if options.mode and options.mode[0].startswith("upstream:"):
            mode = UpstreamMode.parse(options.mode[0])
            assert isinstance(mode, UpstreamMode)  # remove once mypy supports Self.
            context.server.via = flow.server_conn.via = (mode.scheme, mode.address)

        super().__init__(context)

        if options.mode and options.mode[0].startswith("upstream:"):
            self.layer = layers.HttpLayer(context, HTTPMode.upstream)
        else:
            self.layer = layers.HttpLayer(context, HTTPMode.transparent)
        self.layer.connections[client] = MockServer(flow, context.fork())
        self.flow = flow
        self.done = asyncio.Event()

    async def replay(self) -> None:
        await self.server_event(events.Start())
        await self.done.wait()

    def log(
        self,
        message: str,
        level: int = logging.INFO,
        exc_info: Literal[True]
        | tuple[type[BaseException] | None, BaseException | None, TracebackType | None]
        | None = None,
    ) -> None:
        assert isinstance(level, int)
        logger.log(level=level, msg=f"[replay] {message}")

    async def handle_hook(self, hook: commands.StartHook) -> None:
        (data,) = hook.args()
        await ctx.master.addons.handle_lifecycle(hook)
        if isinstance(data, flow.Flow):
            await data.wait_for_resume()
        if isinstance(hook, (layers.http.HttpResponseHook, layers.http.HttpErrorHook)):
            if self.transports:
                # close server connections
                for x in self.transports.values():
                    if x.handler:
                        x.handler.cancel()
                await asyncio.wait(
                    [x.handler for x in self.transports.values() if x.handler]
                )
            # signal completion
            self.done.set()


class ClientPlayback:
    playback_task: asyncio.Task | None = None
    inflight: http.HTTPFlow | None
    queue: asyncio.Queue
    options: Options
    replay_tasks: set[asyncio.Task]

    def __init__(self):
        self.queue = asyncio.Queue()
        self.inflight = None
        self.task = None
        self.replay_tasks = set()

    def running(self):
        self.options = ctx.options
        self.playback_task = asyncio_utils.create_task(
            self.playback(),
            name="client playback",
            keep_ref=False,
        )

    async def done(self):
        if self.playback_task:
            self.playback_task.cancel()
            try:
                await self.playback_task
            except asyncio.CancelledError:
                pass

    async def playback(self):
        while True:
            self.inflight = await self.queue.get()
            try:
                assert self.inflight
                h = ReplayHandler(self.inflight, self.options)
                if ctx.options.client_replay_concurrency == -1:
                    t = asyncio_utils.create_task(
                        h.replay(),
                        name="client playback awaiting response",
                        keep_ref=False,
                    )
                    # keep a reference so this is not garbage collected
                    self.replay_tasks.add(t)
                    t.add_done_callback(self.replay_tasks.remove)
                else:
                    await h.replay()
            except Exception:
                logger.exception(f"Client replay has crashed!")
            self.queue.task_done()
            self.inflight = None

    def check(self, f: flow.Flow) -> str | None:
        if f.live or f == self.inflight:
            return "Can't replay live flow."
        if f.intercepted:
            return "Can't replay intercepted flow."
        if isinstance(f, http.HTTPFlow):
            if not f.request:
                return "Can't replay flow with missing request."
            if f.request.raw_content is None:
                return "Can't replay flow with missing content."
            if f.websocket is not None:
                return "Can't replay WebSocket flows."
        else:
            return "Can only replay HTTP flows."
        return None

    def load(self, loader):
        loader.add_option(
            "client_replay",
            Sequence[str],
            [],
            "Replay client requests from a saved file.",
        )
        loader.add_option(
            "client_replay_concurrency",
            int,
            1,
            "Concurrency limit on in-flight client replay requests. Currently the only valid values are 1 and -1 (no limit).",
        )

    def configure(self, updated):
        if "client_replay" in updated and ctx.options.client_replay:
            try:
                flows = io.read_flows_from_paths(ctx.options.client_replay)
            except exceptions.FlowReadException as e:
                raise exceptions.OptionsError(str(e))
            self.start_replay(flows)

        if "client_replay_concurrency" in updated:
            if ctx.options.client_replay_concurrency not in [-1, 1]:
                raise exceptions.OptionsError(
                    "Currently the only valid client_replay_concurrency values are -1 and 1."
                )

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
                self.queue.task_done()
                f.revert()
                updated.append(f)

        ctx.master.addons.trigger(UpdateHook(updated))
        logger.log(ALERT, "Client replay queue cleared.")

    @command.command("replay.client")
    def start_replay(self, flows: Sequence[flow.Flow]) -> None:
        """
        Add flows to the replay queue, skipping flows that can't be replayed.
        """
        updated: list[http.HTTPFlow] = []
        for f in flows:
            err = self.check(f)
            if err:
                logger.warning(err)
                continue

            http_flow = cast(http.HTTPFlow, f)

            # Prepare the flow for replay
            http_flow.backup()
            http_flow.is_replay = "request"
            http_flow.response = None
            http_flow.error = None
            self.queue.put_nowait(http_flow)
            updated.append(http_flow)
        ctx.master.addons.trigger(UpdateHook(updated))

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
