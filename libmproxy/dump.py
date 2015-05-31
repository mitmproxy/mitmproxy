from __future__ import absolute_import, print_function
import json
import sys
import os
import netlib.utils
from . import flow, filt, utils
from .protocol import http


class DumpError(Exception):
    pass


class Options(object):
    attributes = [
        "app",
        "app_host",
        "app_port",
        "anticache",
        "anticomp",
        "client_replay",
        "filtstr",
        "flow_detail",
        "keepserving",
        "kill",
        "no_server",
        "nopop",
        "refresh_server_playback",
        "replacements",
        "rfile",
        "rheaders",
        "setheaders",
        "server_replay",
        "scripts",
        "showhost",
        "stickycookie",
        "stickyauth",
        "stream_large_bodies",
        "verbosity",
        "outfile",
        "replay_ignore_content",
        "replay_ignore_params",
        "replay_ignore_payload_params",
        "replay_ignore_host"
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)


def str_response(resp):
    r = "%s %s" % (resp.code, resp.msg)
    if resp.is_replay:
        r = "[replay] " + r
    return r


def str_request(f, showhost):
    if f.client_conn:
        c = f.client_conn.address.host
    else:
        c = "[replay]"
    r = "%s %s %s" % (c, f.request.method, f.request.pretty_url(showhost))
    if f.request.stickycookie:
        r = "[stickycookie] " + r
    return r


class DumpMaster(flow.FlowMaster):
    def __init__(self, server, options, outfile=sys.stdout):
        flow.FlowMaster.__init__(self, server, flow.State())
        self.outfile = outfile
        self.o = options
        self.anticache = options.anticache
        self.anticomp = options.anticomp
        self.showhost = options.showhost
        self.replay_ignore_params = options.replay_ignore_params
        self.replay_ignore_content = options.replay_ignore_content
        self.replay_ignore_host = options.replay_ignore_host
        self.refresh_server_playback = options.refresh_server_playback
        self.replay_ignore_payload_params = options.replay_ignore_payload_params

        self.set_stream_large_bodies(options.stream_large_bodies)

        if options.filtstr:
            self.filt = filt.parse(options.filtstr)
        else:
            self.filt = None

        if options.stickycookie:
            self.set_stickycookie(options.stickycookie)

        if options.stickyauth:
            self.set_stickyauth(options.stickyauth)

        if options.outfile:
            path = os.path.expanduser(options.outfile[0])
            try:
                f = file(path, options.outfile[1])
                self.start_stream(f, self.filt)
            except IOError as v:
                raise DumpError(v.strerror)

        if options.replacements:
            for i in options.replacements:
                self.replacehooks.add(*i)

        if options.setheaders:
            for i in options.setheaders:
                self.setheaders.add(*i)

        if options.server_replay:
            self.start_server_playback(
                self._readflow(options.server_replay),
                options.kill, options.rheaders,
                not options.keepserving,
                options.nopop,
                options.replay_ignore_params,
                options.replay_ignore_content,
                options.replay_ignore_payload_params,
                options.replay_ignore_host
            )

        if options.client_replay:
            self.start_client_playback(
                self._readflow(options.client_replay),
                not options.keepserving
            )

        scripts = options.scripts or []
        for command in scripts:
            err = self.load_script(command)
            if err:
                raise DumpError(err)

        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except flow.FlowReadError as v:
                self.add_event("Flow file corrupted.", "error")
                raise DumpError(v)

        if self.o.app:
            self.start_app(self.o.app_host, self.o.app_port)

    def _readflow(self, paths):
        """
        Utitility function that reads a list of flows
        or raises a DumpError if that fails.
        """
        try:
            return flow.read_flows_from_paths(paths)
        except flow.FlowReadError as e:
            raise DumpError(e.strerror)

    def add_event(self, e, level="info"):
        needed = dict(error=0, info=1, debug=2).get(level, 1)
        if self.o.verbosity >= needed:
            print(e, file=self.outfile)
            self.outfile.flush()

    @staticmethod
    def indent(n, t):
        l = str(t).strip().splitlines()
        pad = " " * n
        return "\n".join(pad + i for i in l)

    def _print_message(self, message):
        if self.o.flow_detail >= 2:
            print(self.indent(4, message.headers.format()), file=self.outfile)
        if self.o.flow_detail >= 3:
            if message.content == http.CONTENT_MISSING:
                print(self.indent(4, "(content missing)"), file=self.outfile)
            elif message.content:
                print("", file=self.outfile)
                content = message.get_decoded_content()
                if not utils.isBin(content):
                    try:
                        jsn = json.loads(content)
                        print(
                            self.indent(
                                4,
                                json.dumps(
                                    jsn,
                                    indent=2)),
                            file=self.outfile)
                    except ValueError:
                        print(self.indent(4, content), file=self.outfile)
                else:
                    d = netlib.utils.hexdump(content)
                    d = "\n".join("%s\t%s %s" % i for i in d)
                    print(self.indent(4, d), file=self.outfile)
        if self.o.flow_detail >= 2:
            print("", file=self.outfile)

    def _process_flow(self, f):
        self.state.delete_flow(f)
        if self.filt and not f.match(self.filt):
            return

        if self.o.flow_detail == 0:
            return

        if f.request:
            print(str_request(f, self.showhost), file=self.outfile)
            self._print_message(f.request)

        if f.response:
            if f.response.content == http.CONTENT_MISSING:
                sz = "(content missing)"
            else:
                sz = netlib.utils.pretty_size(len(f.response.content))
            print(
                " << %s %s" %
                (str_response(
                    f.response),
                    sz),
                file=self.outfile)
            self._print_message(f.response)

        if f.error:
            print(" << {}".format(f.error.msg), file=self.outfile)

        self.outfile.flush()

    def handle_request(self, f):
        flow.FlowMaster.handle_request(self, f)
        if f:
            f.reply()
        return f

    def handle_response(self, f):
        flow.FlowMaster.handle_response(self, f)
        if f:
            f.reply()
            self._process_flow(f)
        return f

    def handle_error(self, f):
        flow.FlowMaster.handle_error(self, f)
        if f:
            self._process_flow(f)
        return f

    def shutdown(self):  # pragma: no cover
        return flow.FlowMaster.shutdown(self)

    def run(self):  # pragma: no cover
        if self.o.rfile and not self.o.keepserving:
            self.shutdown()
            return
        try:
            return flow.FlowMaster.run(self)
        except BaseException:
            self.shutdown()
            raise
