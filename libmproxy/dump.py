from __future__ import absolute_import
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
        "wfile",
        "replay_ignore_content",
        "replay_ignore_params",
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)


def str_response(resp):
    r = "%s %s"%(resp.code, resp.msg)
    if resp.is_replay:
        r = "[replay] " + r
    return r


def str_request(f, showhost):
    if f.client_conn:
        c = f.client_conn.address.host
    else:
        c = "[replay]"
    r = "%s %s %s"%(c, f.request.method, f.request.pretty_url(showhost))
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
        self.refresh_server_playback = options.refresh_server_playback

        self.set_stream_large_bodies(options.stream_large_bodies)

        if options.filtstr:
            self.filt = filt.parse(options.filtstr)
        else:
            self.filt = None

        if options.stickycookie:
            self.set_stickycookie(options.stickycookie)

        if options.stickyauth:
            self.set_stickyauth(options.stickyauth)

        if options.wfile:
            path = os.path.expanduser(options.wfile)
            try:
                f = file(path, "wb")
                self.start_stream(f, self.filt)
            except IOError, v:
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
                options.replay_ignore_content
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
            path = os.path.expanduser(options.rfile)
            try:
                f = file(path, "rb")
                freader = flow.FlowReader(f)
            except IOError, v:
                raise DumpError(v.strerror)
            try:
                self.load_flows(freader)
            except flow.FlowReadError, v:
                self.add_event("Flow file corrupted. Stopped loading.", "error")

        if self.o.app:
            self.start_app(self.o.app_host, self.o.app_port)

    def _readflow(self, path):
        path = os.path.expanduser(path)
        try:
            f = file(path, "rb")
            flows = list(flow.FlowReader(f).stream())
        except (IOError, flow.FlowReadError), v:
            raise DumpError(v.strerror)
        return flows

    def add_event(self, e, level="info"):
        needed = dict(error=0, info=1, debug=2).get(level, 1)
        if self.o.verbosity >= needed:
            print >> self.outfile, e
            self.outfile.flush()

    def indent(self, n, t):
        l = str(t).strip().split("\n")
        return "\n".join(" "*n + i for i in l)

    def _process_flow(self, f):
        self.state.delete_flow(f)
        if self.filt and not f.match(self.filt):
            return

        if f.response:
            if self.o.flow_detail > 0:
                if f.response.content == http.CONTENT_MISSING:
                    sz = "(content missing)"
                else:
                    sz = utils.pretty_size(len(f.response.content))
                result = " << %s %s"%(str_response(f.response), sz)
            if self.o.flow_detail > 1:
                result = result + "\n\n" + self.indent(4, f.response.headers)
            if self.o.flow_detail > 2:
                if f.response.content == http.CONTENT_MISSING:
                    cont = self.indent(4, "(content missing)")
                elif utils.isBin(f.response.content):
                    d = netlib.utils.hexdump(f.response.content)
                    d = "\n".join("%s\t%s %s"%i for i in d)
                    cont = self.indent(4, d)
                elif f.response.content:
                    cont = self.indent(4, f.response.content)
                else:
                    cont = ""
                result = result + "\n\n" + cont
        elif f.error:
            result = " << %s"%f.error.msg

        if self.o.flow_detail == 1:
            print >> self.outfile, str_request(f, self.showhost)
            print >> self.outfile, result
        elif self.o.flow_detail == 2:
            print >> self.outfile, str_request(f, self.showhost)
            print >> self.outfile, self.indent(4, f.request.headers)
            print >> self.outfile
            print >> self.outfile, result
            print >> self.outfile, "\n"
        elif self.o.flow_detail >= 3:
            print >> self.outfile, str_request(f, self.showhost)
            print >> self.outfile, self.indent(4, f.request.headers)
            if f.request.content != http.CONTENT_MISSING and utils.isBin(f.request.content):
                d = netlib.utils.hexdump(f.request.content)
                d = "\n".join("%s\t%s %s"%i for i in d)
                print >> self.outfile, self.indent(4, d)
            elif f.request.content:
                print >> self.outfile, self.indent(4, f.request.content)
            print >> self.outfile
            print >> self.outfile, result
            print >> self.outfile, "\n"
        if self.o.flow_detail:
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
