
class AddHeadersResource:

    def addon_path(self):
        return "additional_headers"

    def __init__(self, additional_headers_addon):
        self.additional_headers_addon = additional_headers_addon

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)

    def on_add_headers(self, req, resp):
        for k, v in req.params.items():
            self.additional_headers_addon.headers[k] = v

    def on_add_header(self, req, resp):
        for k, v in req.params.items():
            self.additional_headers_addon.headers[k] = v

    def on_remove_header(self, req, resp):
        self.additional_headers_addon.headers.pop(req.get_param('name'))

    def on_remove_all_headers(self, req, resp):
        self.additional_headers_addon.headers = {}

class AddHeadersAddOn:

    def __init__(self):
        self.num = 0
        self.headers = {}

    def get_resource(self):
        return AddHeadersResource(self)

    def request(self, flow):

        for k, v in self.headers.items():
            flow.request.headers[k] = v

addons = [
    AddHeadersAddOn()
]