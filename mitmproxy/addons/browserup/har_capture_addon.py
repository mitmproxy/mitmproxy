import mitmproxy.http
from mitmproxy import ctx
from mitmproxy.addons.browserup.har.har_resources import HarResource, HarPageResource, HarCaptureTypesResource, \
                                                         PresentResource, NotPresentResource, SizeResource, \
                                                         SLAResource, ErrorResource, CounterResource, \
                                                         HealthCheckResource
from mitmproxy.addons.browserup.har.har_manager import HarManagerMixin
from mitmproxy.addons.browserup.har.flow_capture import FlowCaptureMixin
from mitmproxy.addons.browserup.har import flow_har_entry_patch
flow_har_entry_patch.patch_flow()  # patch flow object with a har entry method


class HarCaptureAddOn(FlowCaptureMixin, HarManagerMixin):

    def load(self, l):
        ctx.log.info('Loading HarCaptureAddon')
        l.add_option("harcapture", str, "", "HAR capture path.")

    def get_resources(self):
        return [HarResource(self),
                HarPageResource(self),
                HarCaptureTypesResource(self),
                PresentResource(self),
                NotPresentResource(self),
                SizeResource(self),
                SLAResource(self),
                ErrorResource(self),
                CounterResource(self),
                HealthCheckResource()
                ]

    def websocket_message(self, flow: mitmproxy.http.HTTPFlow):
        if 'blocklisted' in flow.metadata:
            return
        self.capture_websocket_message(flow)

    def request(self, flow: mitmproxy.http.HTTPFlow):
        if 'blocklisted' in flow.metadata:
            return
        self.capture_request(flow)

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if 'blocklisted' in flow.metadata:
            ctx.log.debug('Blocklist filtered, return nothing.')
            return
        self.capture_response(flow)


addons = [
    HarCaptureAddOn()
]
