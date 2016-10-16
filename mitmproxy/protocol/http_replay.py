from __future__ import absolute_import, print_function, division

import traceback

import netlib.exceptions
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import models
from netlib.http import http1
from netlib import basethread


# TODO: Doesn't really belong into mitmproxy.protocol...


class RequestReplayThread(basethread.BaseThread):
    name = "RequestReplayThread"

    def __init__(self, config, flow, event_queue, should_exit):
        """
            event_queue can be a queue or None, if no scripthooks should be
            processed.
        """
        self.config, self.flow = config, flow
        flow.live = True
        if event_queue:
            self.channel = controller.Channel(event_queue, should_exit)
        else:
            self.channel = None
        super(RequestReplayThread, self).__init__(
            "RequestReplay (%s)" % flow.request.url
        )

    def run(self):
        r = self.flow.request
        first_line_format_backup = r.first_line_format
        server = None
        try:
            self.flow.response = None

            # If we have a channel, run script hooks.
            if self.channel:
                request_reply = self.channel.ask("request", self.flow)
                if isinstance(request_reply, models.HTTPResponse):
                    self.flow.response = request_reply

            if not self.flow.response:
                # In all modes, we directly connect to the server displayed
                if self.config.options.mode == "upstream":
                    server_address = self.config.upstream_server.address
                    server = models.ServerConnection(server_address, (self.config.options.listen_host, 0))
                    server.connect()
                    if r.scheme == "https":
                        connect_request = models.make_connect_request((r.data.host, r.port))
                        server.wfile.write(http1.assemble_request(connect_request))
                        server.wfile.flush()
                        resp = http1.read_response(
                            server.rfile,
                            connect_request,
                            body_size_limit=self.config.options.body_size_limit
                        )
                        if resp.status_code != 200:
                            raise exceptions.ReplayException("Upstream server refuses CONNECT request")
                        server.establish_ssl(
                            self.config.clientcerts,
                            sni=self.flow.server_conn.sni
                        )
                        r.first_line_format = "relative"
                    else:
                        r.first_line_format = "absolute"
                else:
                    server_address = (r.host, r.port)
                    server = models.ServerConnection(server_address, (self.config.options.listen_host, 0))
                    server.connect()
                    if r.scheme == "https":
                        server.establish_ssl(
                            self.config.clientcerts,
                            sni=self.flow.server_conn.sni
                        )
                    r.first_line_format = "relative"

                server.wfile.write(http1.assemble_request(r))
                server.wfile.flush()
                self.flow.server_conn = server
                self.flow.response = models.HTTPResponse.wrap(http1.read_response(
                    server.rfile,
                    r,
                    body_size_limit=self.config.options.body_size_limit
                ))
            if self.channel:
                response_reply = self.channel.ask("response", self.flow)
                if response_reply == exceptions.Kill:
                    raise exceptions.Kill()
        except (exceptions.ReplayException, netlib.exceptions.NetlibException) as e:
            self.flow.error = models.Error(str(e))
            if self.channel:
                self.channel.ask("error", self.flow)
        except exceptions.Kill:
            # Kill should only be raised if there's a channel in the
            # first place.
            self.channel.tell("log", controller.LogEntry("Connection killed", "info"))
        except Exception:
            self.channel.tell("log", controller.LogEntry(traceback.format_exc(), "error"))
        finally:
            r.first_line_format = first_line_format_backup
            self.flow.live = False
            if server:
                server.finish()
