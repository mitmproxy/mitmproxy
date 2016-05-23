import os

import sys
from typing import List, Optional

from .. import controller, script, onboarding, filt
from ..exceptions import Kill, FlowReadException
from .io import FilteredFlowWriter, FlowReader
from .modules import (
    StickyAuthState, ReplaceHooks, SetHeaders, AppRegistry, ClientPlaybackState,
    ServerPlaybackState, StickyCookieState, StreamLargeBodies
)
from ..models import ClientConnection, ServerConnection, HTTPFlow, HTTPRequest
from ..protocol.http_replay import RequestReplayThread
from ..proxy.config import HostMatcher
from netlib.exceptions import HttpException
from netlib.http import Headers


class FlowMaster(controller.ServerMaster):
    @property
    def server(self):
        # At some point, we may want to have support for multiple servers.
        # For now, this suffices.
        if len(self.servers) > 0:
            return self.servers[0]

    def __init__(self, server, state):
        super(FlowMaster, self).__init__()
        if server:
            self.add_server(server)
        self.state = state
        self.server_playback = None
        self.client_playback = None
        self.kill_nonreplay = False
        self.scripts = []  # type: List[script.Script]
        self.pause_scripts = False

        self.stickycookie_state = None  # type: Optional[StickyCookieState]
        self.stickycookie_txt = None

        self.stickyauth_state = False  # type: Optional[StickyAuthState]
        self.stickyauth_txt = None

        self.anticache = False
        self.anticomp = False
        self.stream_large_bodies = None  # type: Optional[StreamLargeBodies]
        self.refresh_server_playback = False
        self.replacehooks = ReplaceHooks()
        self.setheaders = SetHeaders()
        self.replay_ignore_params = False
        self.replay_ignore_content = None
        self.replay_ignore_host = False

        self.stream = None
        self.apps = AppRegistry()

    def start_app(self, host, port):
        self.apps.add(
            onboarding.app,
            host,
            port
        )

    def add_event(self, e, level="info"):
        """
            level: debug, info, error
        """

    def unload_scripts(self):
        for s in self.scripts[:]:
            self.unload_script(s)

    def unload_script(self, script_obj):
        try:
            script_obj.unload()
        except script.ScriptException as e:
            self.add_event("Script error:\n" + str(e), "error")
        script.reloader.unwatch(script_obj)
        self.scripts.remove(script_obj)

    def load_script(self, command, use_reloader=False):
        """
            Loads a script.

            Raises:
                ScriptException
        """
        s = script.Script(command, script.ScriptContext(self))
        s.load()
        if use_reloader:
            script.reloader.watch(s, lambda: self.event_queue.put(("script_change", s)))
        self.scripts.append(s)

    def _run_single_script_hook(self, script_obj, name, *args, **kwargs):
        if script_obj and not self.pause_scripts:
            try:
                script_obj.run(name, *args, **kwargs)
            except script.ScriptException as e:
                self.add_event("Script error:\n{}".format(e), "error")

    def run_script_hook(self, name, *args, **kwargs):
        for script_obj in self.scripts:
            self._run_single_script_hook(script_obj, name, *args, **kwargs)

    def get_ignore_filter(self):
        return self.server.config.check_ignore.patterns

    def set_ignore_filter(self, host_patterns):
        self.server.config.check_ignore = HostMatcher(host_patterns)

    def get_tcp_filter(self):
        return self.server.config.check_tcp.patterns

    def set_tcp_filter(self, host_patterns):
        self.server.config.check_tcp = HostMatcher(host_patterns)

    def set_stickycookie(self, txt):
        if txt:
            flt = filt.parse(txt)
            if not flt:
                return "Invalid filter expression."
            self.stickycookie_state = StickyCookieState(flt)
            self.stickycookie_txt = txt
        else:
            self.stickycookie_state = None
            self.stickycookie_txt = None

    def set_stream_large_bodies(self, max_size):
        if max_size is not None:
            self.stream_large_bodies = StreamLargeBodies(max_size)
        else:
            self.stream_large_bodies = False

    def set_stickyauth(self, txt):
        if txt:
            flt = filt.parse(txt)
            if not flt:
                return "Invalid filter expression."
            self.stickyauth_state = StickyAuthState(flt)
            self.stickyauth_txt = txt
        else:
            self.stickyauth_state = None
            self.stickyauth_txt = None

    def start_client_playback(self, flows, exit):
        """
            flows: List of flows.
        """
        self.client_playback = ClientPlaybackState(flows, exit)

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
        self.server_playback = ServerPlaybackState(
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
            This method should be called by child classes in the handle_request
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
        f2 = f.copy()
        self.load_flow(f2)
        return f2

    def create_request(self, method, scheme, host, port, path):
        """
            this method creates a new artificial and minimalist request also adds it to flowlist
        """
        c = ClientConnection.make_dummy(("", 0))
        s = ServerConnection.make_dummy((host, port))

        f = HTTPFlow(c, s)
        headers = Headers()

        req = HTTPRequest(
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
        if isinstance(f, HTTPFlow):
            if self.server and self.server.config.mode == "reverse":
                f.request.host = self.server.config.upstream_server.address.host
                f.request.port = self.server.config.upstream_server.address.port
                f.request.scheme = self.server.config.upstream_server.scheme

            f.reply = controller.DummyReply()
            if f.request:
                self.handle_request(f)
            if f.response:
                self.handle_responseheaders(f)
                self.handle_response(f)
            if f.error:
                self.handle_error(f)
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
                freader = FlowReader(sys.stdin)
                return self.load_flows(freader)
            else:
                with open(path, "rb") as f:
                    freader = FlowReader(f)
                    return self.load_flows(freader)
        except IOError as v:
            raise FlowReadException(v.strerror)

    def process_new_request(self, f):
        if self.stickycookie_state:
            self.stickycookie_state.handle_request(f)
        if self.stickyauth_state:
            self.stickyauth_state.handle_request(f)

        if self.anticache:
            f.request.anticache()
        if self.anticomp:
            f.request.anticomp()

        if self.server_playback:
            pb = self.do_server_playback(f)
            if not pb and self.kill_nonreplay:
                f.kill(self)

    def process_new_response(self, f):
        if self.stickycookie_state:
            self.stickycookie_state.handle_response(f)

    def replay_request(self, f, block=False, run_scripthooks=True):
        """
            Returns None if successful, or error message if not.
        """
        if f.live and run_scripthooks:
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
            rt = RequestReplayThread(
                self.server.config,
                f,
                self.event_queue if run_scripthooks else False,
                self.should_exit
            )
            rt.start()  # pragma: no cover
            if block:
                rt.join()

    def handle_log(self, l):
        self.add_event(l.msg, l.level)
        l.reply()

    def handle_clientconnect(self, root_layer):
        self.run_script_hook("clientconnect", root_layer)
        root_layer.reply()

    def handle_clientdisconnect(self, root_layer):
        self.run_script_hook("clientdisconnect", root_layer)
        root_layer.reply()

    def handle_serverconnect(self, server_conn):
        self.run_script_hook("serverconnect", server_conn)
        server_conn.reply()

    def handle_serverdisconnect(self, server_conn):
        self.run_script_hook("serverdisconnect", server_conn)
        server_conn.reply()

    def handle_next_layer(self, top_layer):
        self.run_script_hook("next_layer", top_layer)
        top_layer.reply()

    def handle_error(self, f):
        self.state.update_flow(f)
        self.run_script_hook("error", f)
        if self.client_playback:
            self.client_playback.clear(f)
        f.reply()
        return f

    def handle_request(self, f):
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
                f.reply(Kill)
                return
        if f not in self.state.flows:  # don't add again on replay
            self.state.add_flow(f)
        self.replacehooks.run(f)
        self.setheaders.run(f)
        self.process_new_request(f)
        self.run_script_hook("request", f)
        return f

    def handle_responseheaders(self, f):
        try:
            if self.stream_large_bodies:
                self.stream_large_bodies.run(f, False)
        except HttpException:
            f.reply(Kill)
            return

        self.run_script_hook("responseheaders", f)

        f.reply()
        return f

    def handle_response(self, f):
        self.state.update_flow(f)
        self.replacehooks.run(f)
        self.setheaders.run(f)
        self.run_script_hook("response", f)
        if self.client_playback:
            self.client_playback.clear(f)
        self.process_new_response(f)
        if self.stream:
            self.stream.add(f)
        return f

    def handle_intercept(self, f):
        self.state.update_flow(f)

    def handle_accept_intercept(self, f):
        self.state.update_flow(f)

    def handle_script_change(self, s):
        """
        Handle a script whose contents have been changed on the file system.

        Args:
            s (script.Script): the changed script

        Returns:
            True, if reloading was successful.
            False, otherwise.
        """
        ok = True
        # We deliberately do not want to fail here.
        # In the worst case, we have an "empty" script object.
        try:
            s.unload()
        except script.ScriptException as e:
            ok = False
            self.add_event('Error reloading "{}":\n{}'.format(s.filename, e), 'error')
        try:
            s.load()
        except script.ScriptException as e:
            ok = False
            self.add_event('Error reloading "{}":\n{}'.format(s.filename, e), 'error')
        else:
            self.add_event('"{}" reloaded.'.format(s.filename), 'info')
        return ok

    def handle_tcp_message(self, m):
        self.run_script_hook("tcp_message", m)
        m.reply()

    def shutdown(self):
        super(FlowMaster, self).shutdown()

        # Add all flows that are still active
        if self.stream:
            for i in self.state.flows:
                if not i.response:
                    self.stream.add(i)
            self.stop_stream()

        self.unload_scripts()

    def start_stream(self, fp, filt):
        self.stream = FilteredFlowWriter(fp, filt)

    def stop_stream(self):
        self.stream.fo.close()
        self.stream = None

    def start_stream_to_path(self, path, mode="wb", filt=None):
        path = os.path.expanduser(path)
        try:
            f = open(path, mode)
            self.start_stream(f, filt)
        except IOError as v:
            return str(v)
        self.stream_path = path
