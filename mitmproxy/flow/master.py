from __future__ import absolute_import, print_function, division

import os
import sys

from typing import List, Optional, Set  # noqa

import netlib.exceptions
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import models
from mitmproxy.flow import io
from mitmproxy.flow import modules
from mitmproxy.onboarding import app
from mitmproxy.protocol import http_replay
from mitmproxy.proxy.config import HostMatcher
from netlib import strutils


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
        self.active_flows = set()  # type: Set[models.Flow]
        self.server_playback = None  # type: Optional[modules.ServerPlaybackState]
        self.client_playback = None  # type: Optional[modules.ClientPlaybackState]
        self.kill_nonreplay = False

        self.refresh_server_playback = False
        self.replacehooks = modules.ReplaceHooks()
        self.setheaders = modules.SetHeaders()
        self.replay_ignore_params = False
        self.replay_ignore_content = None
        self.replay_ignore_host = False

        self.apps = modules.AppRegistry()

    def start_app(self, host, port):
        self.apps.add(
            app.mapp,
            host,
            port
        )

    def add_event(self, e, level="info"):
        """
            level: debug, info, error
        """

    def get_ignore_filter(self):
        return self.server.config.check_ignore.patterns

    def set_ignore_filter(self, host_patterns):
        self.server.config.check_ignore = HostMatcher(host_patterns)

    def get_tcp_filter(self):
        return self.server.config.check_tcp.patterns

    def set_tcp_filter(self, host_patterns):
        self.server.config.check_tcp = HostMatcher(host_patterns)

    def set_stream_large_bodies(self, max_size):
        if max_size is not None:
            self.stream_large_bodies = modules.StreamLargeBodies(max_size)
        else:
            self.stream_large_bodies = False

    def start_client_playback(self, flows, exit):
        """
            flows: List of flows.
        """
        self.client_playback = modules.ClientPlaybackState(flows, exit)

    def stop_client_playback(self):
        self.client_playback = None

    def start_server_playback(
            self,
            flows,
            kill,
            headers,
            exit,
            nopop,
            ignore_params,
            ignore_content,
            ignore_payload_params,
            ignore_host):
        """
            flows: List of flows.
            kill: Boolean, should we kill requests not part of the replay?
            ignore_params: list of parameters to ignore in server replay
            ignore_content: true if request content should be ignored in server replay
            ignore_payload_params: list of content params to ignore in server replay
            ignore_host: true if request host should be ignored in server replay
        """
        self.server_playback = modules.ServerPlaybackState(
            headers,
            flows,
            exit,
            nopop,
            ignore_params,
            ignore_content,
            ignore_payload_params,
            ignore_host)
        self.kill_nonreplay = kill

    def stop_server_playback(self):
        self.server_playback = None

    def do_server_playback(self, flow):
        """
            This method should be called by child classes in the request
            handler. Returns True if playback has taken place, None if not.
        """
        if self.server_playback:
            rflow = self.server_playback.next_flow(flow)
            if not rflow:
                return None
            response = rflow.response.copy()
            response.is_replay = True
            if self.refresh_server_playback:
                response.refresh()
            flow.response = response
            return True
        return None

    def tick(self, timeout):
        if self.client_playback:
            stop = (
                self.client_playback.done() and
                self.state.active_flow_count() == 0
            )
            exit = self.client_playback.exit
            if stop:
                self.stop_client_playback()
                if exit:
                    self.shutdown()
            else:
                self.client_playback.tick(self)

        if self.server_playback:
            stop = (
                self.server_playback.count() == 0 and
                self.state.active_flow_count() == 0 and
                not self.kill_nonreplay
            )
            exit = self.server_playback.exit
            if stop:
                self.stop_server_playback()
                if exit:
                    self.shutdown()
        return super(FlowMaster, self).tick(timeout)

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
        headers = models.Headers()

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
            if self.server and self.server.config.mode == "reverse":
                f.request.host = self.server.config.upstream_server.address.host
                f.request.port = self.server.config.upstream_server.address.port
                f.request.scheme = self.server.config.upstream_server.scheme

            f.reply = controller.DummyReply()
            if f.request:
                self.request(f)
            if f.response:
                self.responseheaders(f)
                self.response(f)
            if f.error:
                self.error(f)
        elif isinstance(f, models.TCPFlow):
            messages = f.messages
            f.messages = []
            f.reply = controller.DummyReply()
            self.tcp_open(f)
            while messages:
                f.messages.append(messages.pop(0))
                self.tcp_message(f)
            if f.error:
                self.tcp_error(f)
            self.tcp_close(f)
        else:
            raise NotImplementedError()

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

    def process_new_request(self, f):
        if self.server_playback:
            pb = self.do_server_playback(f)
            if not pb and self.kill_nonreplay:
                f.kill(self)

    def replay_request(self, f, block=False):
        """
            Returns None if successful, or error message if not.
        """
        if f.live:
            return "Can't replay live request."
        if f.intercepted:
            return "Can't replay while intercepting..."
        if f.request.content is None:
            return "Can't replay request with missing content..."
        if f.request:
            f.backup()
            f.request.is_replay = True
            if "Content-Length" in f.request.headers:
                f.request.headers["Content-Length"] = str(len(f.request.content))
            f.response = None
            f.error = None
            self.process_new_request(f)
            rt = http_replay.RequestReplayThread(
                self.server.config,
                f,
                self.event_queue,
                self.should_exit
            )
            rt.start()  # pragma: no cover
            if block:
                rt.join()

    def handle_intercept(self, f):
        self.state.update_flow(f)

    def handle_accept_intercept(self, f):
        self.state.update_flow(f)

    def shutdown(self):
        super(FlowMaster, self).shutdown()

    @controller.handler
    def tcp_open(self, flow):
        # TODO: This would break mitmproxy currently.
        # self.state.add_flow(flow)
        self.active_flows.add(flow)

    @controller.handler
    def tcp_message(self, flow):
        message = flow.messages[-1]
        direction = "->" if message.from_client else "<-"
        self.add_event("{client} {direction} tcp {direction} {server}".format(
            client=repr(flow.client_conn.address),
            server=repr(flow.server_conn.address),
            direction=direction,
        ), "info")
        self.add_event(strutils.clean_bin(message.content), "debug")

    @controller.handler
    def tcp_error(self, flow):
        self.add_event("Error in TCP connection to {}: {}".format(
            repr(flow.server_conn.address),
            flow.error
        ), "info")

    @controller.handler
    def tcp_close(self, flow):
        self.active_flows.discard(flow)

    @controller.handler
    def log(self, l):
        self.add_event(l.msg, l.level)

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
        if self.client_playback:
            self.client_playback.clear(f)

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
                    self.add_event("Error in wsgi app. %s" % err, "error")
                f.reply.kill()
                return
        if f not in self.state.flows:  # don't add again on replay
            self.state.add_flow(f)
        self.active_flows.add(f)
        if not f.reply.acked:
            self.replacehooks.run(f)
        if not f.reply.acked:
            self.setheaders.run(f)
        if not f.reply.acked:
            self.process_new_request(f)

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
        self.active_flows.discard(f)
        self.state.update_flow(f)
        if not f.reply.acked:
            self.replacehooks.run(f)
        if not f.reply.acked:
            self.setheaders.run(f)
        if not f.reply.acked:
            if self.client_playback:
                self.client_playback.clear(f)
