from libmproxy import controller, proxy

proxy.config = proxy.Config(
    "~/.mitmproxy/cert.pem"
)

class StickyMaster(controller.Master):
    def __init__(self, server):
        controller.Master.__init__(self, server)
        self.stickyhosts = {}

    def run(self):
        try:
            return controller.Master.run(self)
        except KeyboardInterrupt:
            self.shutdown()

    def handle_request(self, msg):
        hid = (msg.host, msg.port)
        if msg.headers.has_key("cookie"):
            self.stickyhosts[hid] = msg.headers["cookie"]
        elif hid in self.stickyhosts:
            msg.headers["cookie"] = self.stickyhosts[hid]
        msg.ack()

    def handle_response(self, msg):
        hid = (msg.request.host, msg.request.port)
        if msg.headers.has_key("set-cookie"):
            self.stickyhosts[hid] = f.response.headers["set-cookie"]
        msg.ack()


server = proxy.ProxyServer(8080)
m = StickyMaster(server)
m.run()
