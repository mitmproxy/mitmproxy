import sys, os
import flow, filt, utils, script

class DumpError(Exception): pass


class Options(object):
    __slots__ = [
        "anticache",
        "anticomp",
        "client_replay",
        "eventlog",
        "keepserving",
        "kill",
        "no_server",
        "refresh_server_playback",
        "rfile",
        "rheaders",
        "server_replay",
        "script",
        "stickycookie",
        "stickyauth",
        "verbosity",
        "wfile",
    ]
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.__slots__:
            if not hasattr(self, i):
                setattr(self, i, None)


def str_response(resp):
    r = "%s %s"%(resp.code, resp.msg)
    if resp.is_replay():
        r = "[replay] " + r
    return r


def str_request(req):
    if req.client_conn:
        c = req.client_conn.address[0]
    else:
        c = "[replay]"
    r = "%s %s %s"%(c, req.method, req.get_url())
    if req.stickycookie:
        r = "[stickycookie] " + r
    return r


class DumpMaster(flow.FlowMaster):
    def __init__(self, server, options, filtstr, outfile=sys.stdout):
        flow.FlowMaster.__init__(self, server, flow.State())
        self.outfile = outfile
        self.o = options
        self.anticache = options.anticache
        self.anticomp = options.anticomp
        self.eventlog = options.eventlog
        self.refresh_server_playback = options.refresh_server_playback

        if filtstr:
            self.filt = filt.parse(filtstr)
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
                self.fwriter = flow.FlowWriter(f)
            except IOError, v:
                raise DumpError(v.strerror)

        if options.server_replay:
            self.start_server_playback(
                self._readflow(options.server_replay),
                options.kill, options.rheaders,
                not options.keepserving
            )

        if options.client_replay:
            self.start_client_playback(
                self._readflow(options.client_replay),
                not options.keepserving
            )

        if options.script:
            err = self.load_script(options.script)
            if err:
                raise DumpError(err)

        if options.rfile:
            path = os.path.expanduser(options.rfile)
            try:
                f = file(path, "r")
                freader = flow.FlowReader(f)
            except IOError, v:
                raise DumpError(v.strerror)
            self.load_flows(freader)


    def _readflow(self, path):
        path = os.path.expanduser(path)
        try:
            f = file(path, "r")
            flows = list(flow.FlowReader(f).stream())
        except (IOError, flow.FlowReadError), v:
            raise DumpError(v.strerror)
        return flows

    def add_event(self, e, level="info"):
        if self.eventlog:
            print >> self.outfile, e

    def handle_request(self, r):
        f = flow.FlowMaster.handle_request(self, r)
        self.add_event("Request: %s"%str_request(r))
        if f:
            r._ack()
        return f

    def indent(self, n, t):
        l = str(t).strip().split("\n")
        return "\n".join(" "*n + i for i in l)

    def _process_flow(self, f):
        if self.filt and not f.match(self.filt):
            return

        if f.response:
            sz = utils.pretty_size(len(f.response.content))
            if self.o.verbosity > 0:
                result = " << %s %s"%(str_response(f.response), sz)
            if self.o.verbosity > 1:
                result = result + "\n\n" + self.indent(4, f.response.headers)
            if self.o.verbosity > 2:
                if utils.isBin(f.response.content):
                    d = utils.hexdump(f.response.content)
                    d = "\n".join("%s\t%s %s"%i for i in d)
                    cont = self.indent(4, d)
                elif f.response.content:
                    cont = self.indent(4, f.response.content)
                else:
                    cont = ""
                result = result + "\n\n" + cont
        elif f.error:
            result = " << %s"%f.error.msg

        if self.o.verbosity == 1:
            print >> self.outfile, str_request(f.request)
            print >> self.outfile, result
        elif self.o.verbosity == 2:
            print >> self.outfile, str_request(f.request)
            print >> self.outfile, self.indent(4, f.request.headers)
            print >> self.outfile
            print >> self.outfile, result
            print >> self.outfile, "\n"
        elif self.o.verbosity >= 3:
            print >> self.outfile, str_request(f.request)
            print >> self.outfile, self.indent(4, f.request.headers)
            if utils.isBin(f.request.content):
                print >> self.outfile, self.indent(4, utils.hexdump(f.request.content))
            elif f.request.content:
                print >> self.outfile, self.indent(4, f.request.content)
            print >> self.outfile
            print >> self.outfile, result
            print >> self.outfile, "\n"

        self.state.delete_flow(f)
        if self.o.wfile:
            self.fwriter.add(f)

    def handle_response(self, msg):
        f = flow.FlowMaster.handle_response(self, msg)
        if f:
            msg._ack()
            self._process_flow(f)
        return f

    def handle_error(self, msg):
        f = flow.FlowMaster.handle_error(self, msg)
        if f:
            msg._ack()
            self._process_flow(f)
        return f

# begin nocover
    def run(self):
        if self.o.rfile and not self.o.keepserving:
            if self.script:
                self.load_script(None)
            return
        try:
            return flow.FlowMaster.run(self)
        except BaseException:
            self.shutdown()
            raise
