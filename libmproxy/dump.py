import sys, os
import flow, filt

class DumpError(Exception): pass


class Options(object):
    __slots__ = [
        "verbosity",
        "wfile",
    ]
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.__slots__:
            if not hasattr(self, i):
                setattr(self, i, None)


class DumpMaster(flow.FlowMaster):
    def __init__(self, server, options, filtstr, outfile=sys.stdout):
        flow.FlowMaster.__init__(self, server, flow.State())
        self.outfile = outfile
        self.o = options

        if filtstr:
            self.filt = filt.parse(filtstr)
        else:
            self.filt = None

        if options.wfile:
            path = os.path.expanduser(options.wfile)
            try:
                f = file(path, "wb")
                self.fwriter = flow.FlowWriter(f)
            except IOError, v:
                raise DumpError(v.strerror)

    def handle_clientconnection(self, r):
        flow.FlowMaster.handle_clientconnection(self, r)
        r.ack()

    def handle_error(self, r):
        flow.FlowMaster.handle_error(self, r)
        r.ack()

    def handle_request(self, r):
        flow.FlowMaster.handle_request(self, r)
        r.ack()

    def handle_response(self, msg):
        f = flow.FlowMaster.handle_response(self, msg)
        if f:
            msg.ack()
            if self.filt and not f.match(self.filt):
                    return
            if 0 < self.o.verbosity < 3:
                print >> self.outfile, ">>",
                print >> self.outfile, msg.request.short()
            if self.o.verbosity == 1:
                print >> self.outfile, "<<",
                print >> self.outfile, msg.short()
            elif self.o.verbosity == 2:
                print >> self.outfile, "<<"
                for i in msg.assemble().splitlines():
                    print >> self.outfile, "\t", i
                print >> self.outfile, "<<"
            elif self.o.verbosity == 3:
                print >> self.outfile, ">>"
                for i in msg.request.assemble().splitlines():
                    print >> self.outfile, "\t", i
                print >> self.outfile, ">>"
                print >> self.outfile, "<<"
                for i in msg.assemble().splitlines():
                    print >> self.outfile, "\t", i
                print >> self.outfile, "<<"
            self.state.delete_flow(f)
            if self.o.wfile:
                self.fwriter.add(f)


# begin nocover
    def run(self):
        try:
            return flow.FlowMaster.run(self)
        except KeyboardInterrupt:
            self.shutdown()

