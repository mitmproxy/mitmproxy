import sys
import flow

class DumpMaster(flow.FlowMaster):
    def __init__(self, server, verbosity, outfile=sys.stderr):
        self.verbosity, self.outfile = verbosity, outfile
        flow.FlowMaster.__init__(self, server, flow.State())

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
        if 0 < self.verbosity < 3:
            print >> self.outfile, ">>",
            print >> self.outfile, msg.request.short()
        if self.verbosity == 1:
            print >> self.outfile, "<<",
            print >> self.outfile, msg.short()
        elif self.verbosity == 2:
            print >> self.outfile, "<<"
            for i in msg.assemble().splitlines():
                print >> self.outfile, "\t", i
            print >> self.outfile, "<<"
        elif self.verbosity == 3:
            print >> self.outfile, ">>"
            for i in msg.request.assemble().splitlines():
                print >> self.outfile, "\t", i
            print >> self.outfile, ">>"
            print >> self.outfile, "<<"
            for i in msg.assemble().splitlines():
                print >> self.outfile, "\t", i
            print >> self.outfile, "<<"
        msg.ack()


# begin nocover
    def run(self):
        try:
            return flow.FlowMaster.run(self)
        except KeyboardInterrupt:
            self.shutdown()

