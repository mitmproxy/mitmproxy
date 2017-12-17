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
from mitmproxy.net import server_spec
from mitmproxy.net.http import http1
from mitmproxy.coretypes import basethread
from mitmproxy.utils import human


# TODO: Doesn't really belong into mitmproxy.proxy.protocol...


class RequestReplayThread(basethread.BaseThread):
    name = "RequestReplayThread"

    def __init__(
            self,
            opts: options.Options,
            f: http.HTTPFlow,
            event_queue: typing.Optional[queue.Queue],
            should_exit: threading.Event
    ) -> None:
        """
            event_queue can be a queue or None, if no scripthooks should be
            processed.
        """
        self.options = opts
        self.f = f
        f.live = True
        if event_queue:
            self.channel = controller.Channel(event_queue, should_exit)
        else:
            self.channel = None
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
                        server.establish_ssl(
                            self.options.client_certs,
                            sni=self.f.server_conn.sni
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
                        server.establish_ssl(
                            self.options.client_certs,
                            sni=self.f.server_conn.sni
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
