import mitmproxy.http
from mitmproxy import ctx


def patch_flow():
    def set_har_entry(self, updated_entry):
        setattr(self, 'har_entry', updated_entry)

    def get_har_entry(self):
        if hasattr(self, 'har_entry'):
            return self.har_entry
        else:
            addon = ctx.master.addons.get('harcaptureaddon')
            entry = addon.create_har_entry(self)
            setattr(self, 'har_entry', entry)
            return entry

    # Make every flow able to get/carry a har entry reference
    mitmproxy.http.HTTPFlow.get_har_entry = get_har_entry
    mitmproxy.http.HTTPFlow.set_har_entry = set_har_entry
