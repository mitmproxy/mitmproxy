import falcon

class HealthCheckResource:
    def addon_path(self):
        return "healthcheck"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_get(self, req, resp):
        """Gets the Healthcheck.
        ---
        description: Get the healthcheck
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: OK means all is well.
        """
        resp.body = 'OK'
        resp.status = falcon.HTTP_200

class ProxyManagerAddOn:

    def get_resources(self):
        return [HealthCheckResource()]

addons = [
    ProxyManagerAddOn()
]