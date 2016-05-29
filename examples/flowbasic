#!/usr/bin/env python
"""
    This example shows how to build a proxy based on mitmproxy's Flow
    primitives.

    Heads Up: In the majority of cases, you want to use inline scripts.

    Note that request and response messages are not automatically replied to,
    so we need to implement handlers to do this.
"""
from mitmproxy import flow, controller
from mitmproxy.proxy import ProxyServer, ProxyConfig


class MyMaster(flow.FlowMaster):
    def run(self):
        try:
            flow.FlowMaster.run(self)
        except KeyboardInterrupt:
            self.shutdown()

    @controller.handler
    def request(self, f):
        f = flow.FlowMaster.request(self, f)
        print(f)

    @controller.handler
    def response(self, f):
        f = flow.FlowMaster.response(self, f)
        print(f)


config = ProxyConfig(
    port=8080,
    # use ~/.mitmproxy/mitmproxy-ca.pem as default CA file.
    cadir="~/.mitmproxy/"
)
state = flow.State()
server = ProxyServer(config)
m = MyMaster(server, state)
m.run()
