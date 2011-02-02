import sys
import controller

#begin nocover
class DumpMaster(controller.Master):
    """
        A simple master that just dumps to screen.
    """
    def __init__(self, server, verbosity):
        self.verbosity = verbosity
        controller.Master.__init__(self, server)

    def run(self):
        try:
            return controller.Master.run(self)
        except KeyboardInterrupt:
            self.shutdown()

    def handle_response(self, msg):
        if 0 < self.verbosity < 3:
            print >> sys.stderr, ">>",
            print >> sys.stderr, msg.request.short()
        if self.verbosity == 1:
            print >> sys.stderr, "<<",
            print >> sys.stderr, msg.short()
        elif self.verbosity == 2:
            print >> sys.stderr, "<<"
            for i in msg.assemble().splitlines():
                print >> sys.stderr, "\t", i
            print >> sys.stderr, "<<"
        elif self.verbosity == 3:
            print >> sys.stderr, ">>"
            for i in msg.request.assemble().splitlines():
                print >> sys.stderr, "\t", i
            print >> sys.stderr, ">>"
            print >> sys.stderr, "<<"
            for i in msg.assemble().splitlines():
                print >> sys.stderr, "\t", i
            print >> sys.stderr, "<<"
        msg.ack()
