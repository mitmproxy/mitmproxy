from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from types import TracebackType
from typing import cast
from typing import Literal

import wsproto
import wsproto.events

import mitmproxy.types
from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import io
from mitmproxy import websocket
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
from mitmproxy.proxy.layers.websocket import WebsocketEndHook
from mitmproxy.proxy.layers.websocket import WebsocketMessageHook
from mitmproxy.proxy.layers.websocket import WebSocketMessageInjected
from mitmproxy.proxy.mode_specs import UpstreamMode
from mitmproxy.utils import asyncio_utils

logger = logging.getLogger(__name__)


class MockServer(layers.http.HttpConnection):
    """
    A mock HTTP "server" that just pretends it received a full HTTP request,
    which is then processed by the proxy core.
    """

    flow: http.HTTPFlow
    recorded_websocket_messages: list[websocket.WebSocketMessage]
    replay_handler: ReplayHandler | None

    def __init__(
        self,
        flow: http.HTTPFlow,
        context: Context,
        recorded_websocket_messages: list[websocket.WebSocketMessage] | None = None,
        replay_handler: ReplayHandler | None = None,
    ):
        super().__init__(context, context.client)
        self.flow = flow
        self.recorded_websocket_messages = recorded_websocket_messages or []
        self.replay_handler = replay_handler

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
        elif isinstance(event, layers.http.ResponseEndOfMessage):
            # WebsocketLayer is in relay_messages after the 101; start wait-for-reply replay.
            if self.replay_handler and self.flow.websocket:
                self.replay_handler.on_websocket_established()
        elif isinstance(event, events.DataReceived):
            yield layers.http.ReceiveHttp(layers.http.RequestData(1, event.data))
        elif isinstance(event, events.ConnectionClosed):
            if self.flow.websocket:
                yield layers.http.ReceiveHttp(layers.http.RequestEndOfMessage(1))
        elif isinstance(
            event,
            (
                layers.http.ResponseHeaders,
                layers.http.ResponseData,
                layers.http.ResponseTrailers,
                layers.http.ResponseProtocolError,
            ),
        ):
            pass
        else:  # pragma: no cover
            logger.warning(f"Unexpected event during replay: {event}")


class ReplayHandler(server.ConnectionHandler):
    layer: layers.HttpLayer
    recorded_websocket_messages: list[websocket.WebSocketMessage]
    recorded_closed_by_client: bool | None
    recorded_close_code: int | None
    recorded_close_reason: str
    _ws_index: int
    _waiting_for_server: int
    _sending_clients: bool

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

        # HTTP upgrade recreates flow.websocket; keep the captured conversation for later replay.
        if flow.websocket:
            self.recorded_websocket_messages = list(flow.websocket.messages)
            self.recorded_closed_by_client = flow.websocket.closed_by_client
            self.recorded_close_code = flow.websocket.close_code
            self.recorded_close_reason = flow.websocket.close_reason or ""
            flow.websocket = None
        else:
            self.recorded_websocket_messages = []
            self.recorded_closed_by_client = None
            self.recorded_close_code = None
            self.recorded_close_reason = ""
        self._ws_index = 0
        self._waiting_for_server = 0
        self._sending_clients = False

        if options.mode and options.mode[0].startswith("upstream:"):
            self.layer = layers.HttpLayer(context, HTTPMode.upstream)
        else:
            self.layer = layers.HttpLayer(context, HTTPMode.transparent)
        self.layer.connections[client] = MockServer(
            flow, context.fork(), self.recorded_websocket_messages, self
        )
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

    def on_websocket_established(self) -> None:
        asyncio_utils.create_task(
            self._send_next_client_burst(),
            name="websocket client replay",
            keep_ref=True,
        )

    async def _send_next_client_burst(self) -> None:
        if self.done.is_set():
            return
        while not self.done.is_set():
            self._sending_clients = True
            while self._ws_index < len(self.recorded_websocket_messages):
                msg = self.recorded_websocket_messages[self._ws_index]
                if msg.dropped:
                    self._ws_index += 1
                    continue
                if not msg.from_client:
                    break
                self._ws_index += 1
                await self.server_event(WebSocketMessageInjected(self.flow, msg))
            wait = 0
            while self._ws_index < len(self.recorded_websocket_messages):
                msg = self.recorded_websocket_messages[self._ws_index]
                if msg.dropped:
                    self._ws_index += 1
                    continue
                if msg.from_client:
                    break
                wait += 1
                self._ws_index += 1
            self._waiting_for_server += wait
            self._sending_clients = False
            if self._waiting_for_server > 0:
                return
            if self._ws_index >= len(self.recorded_websocket_messages):
                await self._finish_websocket_replay()
                return

    async def _finish_websocket_replay(self) -> None:
        if self.done.is_set():
            return
        if self.recorded_closed_by_client is False:
            # Server closed originally; wait for WebsocketEndHook.
            return
        code = self.recorded_close_code or 1000
        if code in (1005, 1006):
            await self.server_event(events.ConnectionClosed(self.client))
            return
        encoder = wsproto.Connection(wsproto.ConnectionType.CLIENT)
        payload = encoder.send(
            wsproto.events.CloseConnection(code, self.recorded_close_reason)
        )
        await self.server_event(events.DataReceived(self.client, payload))

    async def handle_hook(self, hook: commands.StartHook) -> None:
        (data,) = hook.args()
        await ctx.master.addons.handle_lifecycle(hook)
        if isinstance(data, flow.Flow):
            await data.wait_for_resume()
        if isinstance(hook, layers.http.HttpErrorHook):
            await self._finish()
        elif isinstance(hook, layers.http.HttpResponseHook):
            # WebSocket replay continues after a successful HTTP upgrade.
            if not self.flow.websocket:
                await self._finish()
        elif isinstance(hook, WebsocketMessageHook):
            assert self.flow.websocket
            last = self.flow.websocket.messages[-1]
            if not last.from_client:
                if self._waiting_for_server > 0 or self._sending_clients:
                    self._waiting_for_server -= 1
                    if self._waiting_for_server == 0 and not self._sending_clients:
                        await self._send_next_client_burst()
        elif isinstance(hook, WebsocketEndHook):
            await self._finish()

    async def _finish(self) -> None:
        if self.done.is_set():
            return
        if self.transports:
            # close server connections
            for x in self.transports.values():
                if x.handler:
                    x.handler.cancel()
            await asyncio.wait(
                [x.handler for x in self.transports.values() if x.handler]
            )
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
