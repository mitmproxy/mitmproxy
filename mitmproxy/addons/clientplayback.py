from mitmproxy import log
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy import flow
from mitmproxy import options
from mitmproxy import connections
from mitmproxy.net import server_spec, tls
from mitmproxy.net.http import http1
from mitmproxy.coretypes import basethread
from mitmproxy.utils import human
from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import command
import mitmproxy.types

import typing


class RequestReplayThread(basethread.BaseThread):
    name = "RequestReplayThread"

    def __init__(
            self,
            opts: options.Options,
            f: http.HTTPFlow,
            channel: controller.Channel,
    ) -> None:
        self.options = opts
        self.f = f
        f.live = True
        self.channel = channel
        super().__init__(
            "RequestReplay (%s)" % f.request.url
        )
        self.daemon = True

    def run(self):
        r = self.f.request
        bsl = human.parse_size(self.options.body_size_limit)
        first_line_format_backup = r.first_line_format
        server = None
        try:
            self.f.response = None

            # If we have a channel, run script hooks.
            if self.channel:
                request_reply = self.channel.ask("request", self.f)
                if isinstance(request_reply, http.HTTPResponse):
                    self.f.response = request_reply

            if not self.f.response:
                # In all modes, we directly connect to the server displayed
                if self.options.mode.startswith("upstream:"):
                    server_address = server_spec.parse_with_mode(self.options.mode)[1].address
                    server = connections.ServerConnection(server_address, (self.options.listen_host, 0))
                    server.connect()
                    if r.scheme == "https":
                        connect_request = http.make_connect_request((r.data.host, r.port))
                        server.wfile.write(http1.assemble_request(connect_request))
                        server.wfile.flush()
                        resp = http1.read_response(
                            server.rfile,
                            connect_request,
                            body_size_limit=bsl
                        )
                        if resp.status_code != 200:
                            raise exceptions.ReplayException("Upstream server refuses CONNECT request")
                        server.establish_tls(
                            sni=self.f.server_conn.sni,
                            **tls.client_arguments_from_options(self.options)
                        )
                        r.first_line_format = "relative"
                    else:
                        r.first_line_format = "absolute"
                else:
                    server_address = (r.host, r.port)
                    server = connections.ServerConnection(
                        server_address,
                        (self.options.listen_host, 0)
                    )
                    server.connect()
                    if r.scheme == "https":
                        server.establish_tls(
                            sni=self.f.server_conn.sni,
                            **tls.client_arguments_from_options(self.options)
                        )
                    r.first_line_format = "relative"

                server.wfile.write(http1.assemble_request(r))
                server.wfile.flush()

                if self.f.server_conn:
                    self.f.server_conn.close()
                self.f.server_conn = server

                self.f.response = http.HTTPResponse.wrap(
                    http1.read_response(
                        server.rfile,
                        r,
                        body_size_limit=bsl
                    )
                )
            if self.channel:
                response_reply = self.channel.ask("response", self.f)
                if response_reply == exceptions.Kill:
                    raise exceptions.Kill()
        except (exceptions.ReplayException, exceptions.NetlibException) as e:
            self.f.error = flow.Error(str(e))
            if self.channel:
                self.channel.ask("error", self.f)
        except exceptions.Kill:
            # Kill should only be raised if there's a channel in the
            # first place.
            self.channel.tell(
                "log",
                log.LogEntry("Connection killed", "info")
            )
        except Exception as e:
            self.channel.tell(
                "log",
                log.LogEntry(repr(e), "error")
            )
        finally:
            r.first_line_format = first_line_format_backup
            self.f.live = False
            if server.connected():
                server.finish()


class ClientPlayback:
    def __init__(self):
        self.flows: typing.List[flow.Flow] = []
        self.current_thread = None
        self.configured = False

    def replay_request(
            self,
            f: http.HTTPFlow,
            block: bool=False
    ) -> RequestReplayThread:
        """
        Replay a HTTP request to receive a new response from the server.

        Args:
            f: The flow to replay.
            block: If True, this function will wait for the replay to finish.
                This causes a deadlock if activated in the main thread.

        Returns:
            The thread object doing the replay.

        Raises:
            exceptions.ReplayException, if the flow is in a state
            where it is ineligible for replay.
        """

        if f.live:
            raise exceptions.ReplayException(
                "Can't replay live flow."
            )
        if f.intercepted:
            raise exceptions.ReplayException(
                "Can't replay intercepted flow."
            )
        if not f.request:
            raise exceptions.ReplayException(
                "Can't replay flow with missing request."
            )
        if f.request.raw_content is None:
            raise exceptions.ReplayException(
                "Can't replay flow with missing content."
            )

        f.backup()
        f.request.is_replay = True

        f.response = None
        f.error = None

        if f.request.http_version == "HTTP/2.0":  # https://github.com/mitmproxy/mitmproxy/issues/2197
            f.request.http_version = "HTTP/1.1"
            host = f.request.headers.pop(":authority")
            f.request.headers.insert(0, "host", host)

        rt = RequestReplayThread(ctx.master.options, f, ctx.master.channel)
        rt.start()  # pragma: no cover
        if block:
            rt.join()
        return rt

    def load(self, loader):
        loader.add_option(
            "client_replay", typing.Sequence[str], [],
            "Replay client requests from a saved file."
        )

    def count(self) -> int:
        if self.current_thread:
            current = 1
        else:
            current = 0
        return current + len(self.flows)

    @command.command("replay.client.stop")
    def stop_replay(self) -> None:
        """
            Stop client replay.
        """
        self.flows = []
        ctx.log.alert("Client replay stopped.")
        ctx.master.addons.trigger("update", [])

    @command.command("replay.client")
    def start_replay(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Replay requests from flows.
        """
        for f in flows:
            if f.live:
                raise exceptions.CommandError("Can't replay live flow.")
        self.flows = list(flows)
        ctx.log.alert("Replaying %s flows." % len(self.flows))
        ctx.master.addons.trigger("update", [])

    @command.command("replay.client.file")
    def load_file(self, path: mitmproxy.types.Path) -> None:
        try:
            flows = io.read_flows_from_paths([path])
        except exceptions.FlowReadException as e:
            raise exceptions.CommandError(str(e))
        ctx.log.alert("Replaying %s flows." % len(self.flows))
        self.flows = flows
        ctx.master.addons.trigger("update", [])

    def configure(self, updated):
        if not self.configured and ctx.options.client_replay:
            self.configured = True
            ctx.log.info("Client Replay: {}".format(ctx.options.client_replay))
            try:
                flows = io.read_flows_from_paths(ctx.options.client_replay)
            except exceptions.FlowReadException as e:
                raise exceptions.OptionsError(str(e))
            self.start_replay(flows)

    def tick(self):
        current_is_done = self.current_thread and not self.current_thread.is_alive()
        can_start_new = not self.current_thread or current_is_done
        will_start_new = can_start_new and self.flows

        if current_is_done:
            self.current_thread = None
            ctx.master.addons.trigger("update", [])
        if will_start_new:
            f = self.flows.pop(0)
            self.current_thread = self.replay_request(f)
            ctx.master.addons.trigger("update", [f])
        if current_is_done and not will_start_new:
            ctx.master.addons.trigger("processing_complete")
