from __future__ import (absolute_import, print_function, division)
import threading

from netlib.http import HttpError
from netlib.http.http1 import HTTP1Protocol
from netlib.tcp import NetLibError
from ..controller import Channel
from ..models import Error, HTTPResponse, ServerConnection, make_connect_request
from .base import Kill


# TODO: Doesn't really belong into libmproxy.protocol...


class RequestReplayThread(threading.Thread):
    name = "RequestReplayThread"

    def __init__(self, config, flow, masterq, should_exit):
        """
            masterqueue can be a queue or None, if no scripthooks should be
            processed.
        """
        self.config, self.flow = config, flow
        if masterq:
            self.channel = Channel(masterq, should_exit)
        else:
            self.channel = None
        super(RequestReplayThread, self).__init__()

    def run(self):
        r = self.flow.request
        form_out_backup = r.form_out
        try:
            self.flow.response = None

            # If we have a channel, run script hooks.
            if self.channel:
                request_reply = self.channel.ask("request", self.flow)
                if request_reply == Kill:
                    raise Kill()
                elif isinstance(request_reply, HTTPResponse):
                    self.flow.response = request_reply

            if not self.flow.response:
                # In all modes, we directly connect to the server displayed
                if self.config.mode == "upstream":
                    server_address = self.config.upstream_server.address
                    server = ServerConnection(server_address)
                    server.connect()
                    protocol = HTTP1Protocol(server)
                    if r.scheme == "https":
                        connect_request = make_connect_request((r.host, r.port))
                        server.send(protocol.assemble(connect_request))
                        resp = protocol.read_response("CONNECT")
                        if resp.code != 200:
                            raise HttpError(502, "Upstream server refuses CONNECT request")
                        server.establish_ssl(
                            self.config.clientcerts,
                            sni=self.flow.server_conn.sni
                        )
                        r.form_out = "relative"
                    else:
                        r.form_out = "absolute"
                else:
                    server_address = (r.host, r.port)
                    server = ServerConnection(server_address)
                    server.connect()
                    protocol = HTTP1Protocol(server)
                    if r.scheme == "https":
                        server.establish_ssl(
                            self.config.clientcerts,
                            sni=self.flow.server_conn.sni
                        )
                    r.form_out = "relative"

                server.send(protocol.assemble(r))
                self.flow.server_conn = server
                self.flow.response = HTTPResponse.from_protocol(
                    protocol,
                    r.method,
                    body_size_limit=self.config.body_size_limit,
                )
            if self.channel:
                response_reply = self.channel.ask("response", self.flow)
                if response_reply == Kill:
                    raise Kill()
        except (HttpError, NetLibError) as v:
            self.flow.error = Error(repr(v))
            if self.channel:
                self.channel.ask("error", self.flow)
        except Kill:
            # Kill should only be raised if there's a channel in the
            # first place.
            from ..proxy.root_context import Log
            self.channel.tell("log", Log("Connection killed", "info"))
        finally:
            r.form_out = form_out_backup
