from mitmproxy import ctx

# All addons should be "loaded" before we init flow
class BrowserupInitFlowAddOn:

    def __init__(self):
        self.num = 0

    def request(self, flow):
        ctx.log.debug("request called in addon {}".format(self.__class__.__name__))
        if not hasattr(flow.request, 'har_entry'):
            self.init_har_entry(flow)

    def init_har_entry(self, flow):
        ctx.log.debug("Initializing har entry for flow request: {}".format(str(flow.request)))
        har_dump_addon = ctx.master.addons.get('harcaptureaddon')

        entry = HarBuilder.har_entry()
        setattr(flow.request, 'har_entry', entry)
        har_dump_addon.append_har_entry(entry)

addons = [
    BrowserupInitFlowAddOn()
]