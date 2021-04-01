import mitmproxy.http
from mitmproxy import ctx

def patch_flow():
    def har_entry(self):
        if hasattr(self, 'harentry') and callable(self.harentry):
            return self.harentry
        else:
            if not(hasattr(self, 'har_manager')):
                self.har_manager = ctx.master.addons.get('harcaptureaddon').har_manager
            entry = self.har_manager.create_har_entry(self)
            setattr(self, 'harentry', entry)
            return entry
    # Make every flow able to get/carry a har entry reference
    mitmproxy.http.HTTPFlow.har_entry = har_entry