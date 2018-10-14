import queue
import threading
import typing

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


class RequestReplayThread(basethread.BaseThread):
    daemon = True

    def __init__(
            self,
            opts: options.Options,
            channel: controller.Channel,
            queue: queue.Queue,
    ) -> None:
        self.options = opts
        self.channel = channel
        self.queue = queue
        self.inflight = threading.Event()
        super().__init__("RequestReplayThread")

    def run(self):
        while True:
            f = self.queue.get()
            self.inflight.set()
            self.replay(f)
            self.inflight.clear()

    def replay(self, f):  # pragma: no cover
        f.live = True
        r = f.request
        bsl = human.parse_size(self.options.body_size_limit)
        first_line_format_backup = r.first_line_format
        server = None
        try:
            f.response = None

            # If we have a channel, run script hooks.
            request_reply = self.channel.ask("request", f)
            if isinstance(request_reply, http.HTTPResponse):
                f.response = request_reply

            if not f.response:
                # In all modes, we directly connect to the server displayed
                if self.options.mode.startswith("upstream:"):
                    server_address = server_spec.parse_with_mode(self.options.mode)[1].address
                    server = connections.ServerConnection(server_address)
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
                            raise exceptions.ReplayException(
                                "Upstream server refuses CONNECT request"
                            )
                        server.establish_tls(
                            sni=f.server_conn.sni,
                            **tls.client_arguments_from_options(self.options)
                        )
                        r.first_line_format = "relative"
                    else:
                        r.first_line_format = "absolute"
                else:
                    server_address = (r.host, r.port)
                    server = connections.ServerConnection(server_address)
                    server.connect()
                    if r.scheme == "https":
                        server.establish_tls(
                            sni=f.server_conn.sni,
                            **tls.client_arguments_from_options(self.options)
                        )
                    r.first_line_format = "relative"

                server.wfile.write(http1.assemble_request(r))
                server.wfile.flush()

                if f.server_conn:
                    f.server_conn.close()
                f.server_conn = server

                f.response = http.HTTPResponse.wrap(
                    http1.read_response(server.rfile, r, body_size_limit=bsl)
                )
            response_reply = self.channel.ask("response", f)
            if response_reply == exceptions.Kill:
                raise exceptions.Kill()
        except (exceptions.ReplayException, exceptions.NetlibException) as e:
            f.error = flow.Error(str(e))
            self.channel.ask("error", f)
        except exceptions.Kill:
            self.channel.tell("log", log.LogEntry("Connection killed", "info"))
        except Exception as e:
            self.channel.tell("log", log.LogEntry(repr(e), "error"))
        finally:
            r.first_line_format = first_line_format_backup
            f.live = False
            if server.connected():
                server.finish()
                server.close()


class ClientPlayback:
    def __init__(self):
        self.q = queue.Queue()
        self.thread: RequestReplayThread = None

    def check(self, f: http.HTTPFlow):
        if f.live:
            return "Can't replay live flow."
        if f.intercepted:
            return "Can't replay intercepted flow."
        if not f.request:
            return "Can't replay flow with missing request."
        if f.request.raw_content is None:
            return "Can't replay flow with missing content."

    def load(self, loader):
        loader.add_option(
            "client_replay", typing.Sequence[str], [],
            "Replay client requests from a saved file."
        )

    def running(self):
        self.thread = RequestReplayThread(
            ctx.options,
            ctx.master.channel,
            self.q,
        )
        self.thread.start()

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
        inflight = 1 if self.thread and self.thread.inflight.is_set() else 0
        return self.q.qsize() + inflight

    @command.command("replay.client.stop")
    def stop_replay(self) -> None:
        """
            Clear the replay queue.
        """
        with self.q.mutex:
            lst = list(self.q.queue)
            self.q.queue.clear()
            for f in lst:
                f.revert()
            ctx.master.addons.trigger("update", lst)
        ctx.log.alert("Client replay queue cleared.")

    @command.command("replay.client")
    def start_replay(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Add flows to the replay queue, skipping flows that can't be replayed.
        """
        lst = []
        for f in flows:
            hf = typing.cast(http.HTTPFlow, f)

            err = self.check(hf)
            if err:
                ctx.log.warn(err)
                continue

            lst.append(hf)
            # Prepare the flow for replay
            hf.backup()
            hf.request.is_replay = True
            hf.response = None
            hf.error = None
            # https://github.com/mitmproxy/mitmproxy/issues/2197
            if hf.request.http_version == "HTTP/2.0":
                hf.request.http_version = "HTTP/1.1"
                host = hf.request.headers.pop(":authority")
                hf.request.headers.insert(0, "host", host)
            self.q.put(hf)
        ctx.master.addons.trigger("update", lst)

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
