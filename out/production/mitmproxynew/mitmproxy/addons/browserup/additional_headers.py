from marshmallow import Schema, fields

class HeaderSchema(Schema):
    headers = fields.Dict(required=True,description="Header key-value pairs")

class AddHeadersResource:

    def apispec(self, spec):
        spec.components.schema('Headers', schema=HeaderSchema())
        spec.path(resource=self)

    def addon_path(self):
        return "additional_headers"

    def __init__(self, additional_headers_addon):
        self.additional_headers_addon = additional_headers_addon

    def on_get(self, req, resp):
        """Get the Headers.
        ---
        description: Get the current added Headers
        operationId: getAdditionalHeaders
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: The current header settings.
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/Headers"
        """
        return self.additional_headers_addon.headers

    def on_post(self, req, resp):
        """Post the Headers object to be added in
        ---
        description: Set additional headers to add to requests
        operationId: setAdditionalHeaders
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: Show the current additional header settings.
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/Headers"
        """
        self.additional_headers_addon.headers = req.params.items()

    def on_delete(self, req, resp):
        """Clear the current additional Headers, reseting to adding no additional headers
        ---
        description: Clear the additional Headers
        operationId: clearAdditionalHeaders
        operationId: clearAdditionalHeaders
        tags:
            - BrowserUpProxy
        responses:
            204:
                description: The current additional header settings were cleared.
        """
        self.additional_headers_addon.headers = {}

class AddHeadersAddOn:

    def __init__(self):
        self.num = 0
        self.headers = {}

    def get_resources(self):
        return [AddHeadersResource(self)]

    def request(self, flow):
        for k, v in self.headers.items():
            flow.request.headers[k] = v

addons = [
    AddHeadersAddOn()
]