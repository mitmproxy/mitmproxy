import json
import base64
import typing
import tempfile

from time import sleep

import re

from datetime import datetime
from datetime import timezone

import falcon

from mitmproxy import ctx

#from mitmproxy import connections
from mitmproxy import version
from mitmproxy.utils import strutils
from mitmproxy.net.http import cookies
from mitmproxy import http

class InitFlowResource:

    def addon_path(self):
        return "init_flow"

    def __init__(self, init_flow_addon):
        self.init_flow_addon = init_flow_addon

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)


class InitFlowAddOn:

    def __init__(self):
        self.num = 0

    def get_resource(self):
        return InitFlowResource(self)

    # def http_connect(self, flow):
    #     if not hasattr(flow.request, 'har_entry'):
    #         self.init_har_entry(flow)

    def request(self, flow):
        if not hasattr(flow.request, 'har_entry'):
            self.init_har_entry(flow)

    def init_har_entry(self, flow):
        ctx.log.debug("Initializing har entry for flow request: {}".format(str(flow.request)))
        hardumpaddon = ctx.master.addons.get('hardumpaddon')
        setattr(flow.request, 'har_entry', hardumpaddon.generate_har_entry())
        hardumpaddon.append_har_entry(flow.request.har_entry)

addons = [
    InitFlowAddOn()
]