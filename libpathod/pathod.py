import netlib

class PathodHandler(netlib.BaseHandler):
    def handle(self):
        print "Here"


class PathodServer(netlib.TCPServer):
    def __init__(self, addr):
        netlib.TCPServer.__init__(self, addr)

    def handle_connection(self, request, client_address):
        PathodHandler(request, client_address, self)

