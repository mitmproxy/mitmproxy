from __future__ import absolute_import, print_function, division

import os
import sys

from typing import Optional  # noqa

import netlib.exceptions
from netlib import http
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import models
from mitmproxy.flow import io
from mitmproxy.flow import modules
from mitmproxy.onboarding import app
from mitmproxy.protocol import http_replay


def event_sequence(f):
    if isinstance(f, models.HTTPFlow):
        if f.request:
            yield "requestheaders", f
            yield "request", f
        if f.response:
            yield "responseheaders", f
            yield "response", f
        if f.error:
            yield "error", f
    elif isinstance(f, models.TCPFlow):
        messages = f.messages
        f.messages = []
        f.reply = controller.DummyReply()
        yield "tcp_start", f
        while messages:
            f.messages.append(messages.pop(0))
            yield "tcp_message", f
        if f.error:
            yield "tcp_error", f
        yield "tcp_end", f
    else:
        raise NotImplementedError


class FlowMaster(controller.Master):

    @property
    def server(self):
        # At some point, we may want to have support for multiple servers.
        # For now, this suffices.
        if len(self.servers) > 0:
            return self.servers[0]

    def __init__(self, options, server, state):
        super(FlowMaster, self).__init__(options)
        if server:
            self.add_server(server)
        self.state = state
        self.stream_large_bodies = None  # type: Optional[modules.StreamLargeBodies]
        self.apps = modules.AppRegistry()

    def start_app(self, host, port):
        self.apps.add(app.mapp, host, port)

    def set_stream_large_bodies(self, max_size):
        if max_size is not None:
            self.stream_large_bodies = modules.StreamLargeBodies(max_size)
        else:
            self.stream_large_bodies = False

    def duplicate_flow(self, f):
        """
            Duplicate flow, and insert it into state without triggering any of
            the normal flow events.
        """
        f2 = f.copy()
        self.state.add_flow(f2)
        return f2

    def create_request(self, method, scheme, host, port, path):
        """
            this method creates a new artificial and minimalist request also adds it to flowlist
        """
        c = models.ClientConnection.make_dummy(("", 0))
        s = models.ServerConnection.make_dummy((host, port))

        f = models.HTTPFlow(c, s)
        headers = http.Headers()

        req = models.HTTPRequest(
            "absolute",
            method,
            scheme,
            host,
            port,
            path,
            b"HTTP/1.1",
            headers,
            b""
        )
        f.request = req
        self.load_flow(f)
        return f

    def load_flow(self, f):
        """
        Loads a flow
        """
        if isinstance(f, models.HTTPFlow):
            if self.server and self.options.mode == "reverse":
                f.request.host = self.server.config.upstream_server.address.host
                f.request.port = self.server.config.upstream_server.address.port
                f.request.scheme = self.server.config.upstream_server.scheme
        f.reply = controller.DummyReply()
        for e, o in event_sequence(f):
            getattr(self, e)(o)

    def load_flows(self, fr):
        """
            Load flows from a FlowReader object.
        """
        cnt = 0
        for i in fr.stream():
            cnt += 1
            self.load_flow(i)
        return cnt

    def load_flows_file(self, path):
        path = os.path.expanduser(path)
        try:
            if path == "-":
                # This is incompatible with Python 3 - maybe we can use click?
                freader = io.FlowReader(sys.stdin)
                return self.load_flows(freader)
            else:
                with open(path, "rb") as f:
                    freader = io.FlowReader(f)
                    return self.load_flows(freader)
        except IOError as v:
            raise exceptions.FlowReadException(v.strerror)

    def replay_request(self, f, block=False):
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
        if f.request.raw_content is None:
            raise exceptions.ReplayException(
                "Can't replay flow with missing content."
            )
        if not f.request:
            raise exceptions.ReplayException(
                "Can't replay flow with missing request."
            )

        f.backup()
        f.request.is_replay = True

        f.response = None
        f.error = None

        rt = http_replay.RequestReplayThread(
            self.server.config,
            f,
            self.event_queue,
            self.should_exit
        )
        rt.start()  # pragma: no cover
        if block:
            rt.join()
        return rt

    @controller.handler
    def log(self, l):
        pass

    @controller.handler
    def clientconnect(self, root_layer):
        pass

    @controller.handler
    def clientdisconnect(self, root_layer):
        pass

    @controller.handler
    def serverconnect(self, server_conn):
        pass

    @controller.handler
    def serverdisconnect(self, server_conn):
        pass

    @controller.handler
    def next_layer(self, top_layer):
        pass

    @controller.handler
    def error(self, f):
        self.state.update_flow(f)

    @controller.handler
    def requestheaders(self, f):
        pass

    @controller.handler
    def request(self, f):
        if f.live:
            app = self.apps.get(f.request)
            if app:
                err = app.serve(
                    f,
                    f.client_conn.wfile,
                    **{"mitmproxy.master": self}
                )
                if err:
                    self.add_log("Error in wsgi app. %s" % err, "error")
                f.reply.kill()
                return
        if f not in self.state.flows:  # don't add again on replay
            self.state.add_flow(f)

    @controller.handler
    def responseheaders(self, f):
        try:
            if self.stream_large_bodies:
                self.stream_large_bodies.run(f, False)
        except netlib.exceptions.HttpException:
            f.reply.kill()
            return

    @controller.handler
    def response(self, f):
        self.state.update_flow(f)

    @controller.handler
    def websocket_handshake(self, f):
        pass

    def handle_intercept(self, f):
        self.state.update_flow(f)

    def handle_accept_intercept(self, f):
        self.state.update_flow(f)

    @controller.handler
    def tcp_start(self, flow):
        # TODO: This would break mitmproxy currently.
        # self.state.add_flow(flow)
        pass

    @controller.handler
    def tcp_message(self, flow):
        pass

    @controller.handler
    def tcp_error(self, flow):
        pass

    @controller.handler
    def tcp_end(self, flow):
        pass
