class AuthBasicResource:

    def addon_path(self):
        return "auth_basic"

    def __init__(self, auth_basic_addon):
        self.auth_basic_addon = auth_basic_addon

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)

    def on_auth_authorization(self, req, resp):
        credentials = req.get_param('base64EncodedCredentials')
        domain = req.get_param('domain')
        self.auth_basic_addon.credentials_map[domain] = credentials

    def on_stop_authorization(self, req, resp):
        domain = req.get_param('domain')
        self.auth_basic_addon.credentials_map.pop(domain)

class AuthBasicAddOn:

    def __init__(self):
        self.num = 0
        self.credentials_map = {}

    def get_resource(self):
        return AuthBasicResource(self)

    def request(self, flow):
        if flow.request.host in self.credentials_map:
            flow.request.headers['Authorization'] = 'Basic ' + self.credentials_map[flow.request.host]
