from marshmallow import Schema, fields

class AuthBasic(Schema):
    base_64_credentials = fields.Str(required=True, description="base 64 encoding of the username and password")

class AuthBasicResource:

    def addon_path(self):
        return "auth_basic/{domain}"

    def apispec(self, spec):
        spec.components.schema('AuthBasic', schema=AuthBasic())
        spec.path(resource=self)

    def __init__(self, auth_basic_addon):
        self.auth_basic_addon = auth_basic_addon

    def on_post(self, req, resp, domain):
        """Posts (enables) Automatic basic auth for a domain
        ---
        description: Enables automatic basic auth for a domain
        operationId: setBasicAuth
        parameters:
            - in: path
              name: domain
              required: true
              schema:
                type: string
              description: The domain for which this Basic Auth should be used
        tags:
            - BrowserUpProxy
        requestBody:
            content:
              application/json:
                schema:
                    $ref: "#/components/schemas/AuthBasic"
        responses:
            204:
                description: Success!
        """
        credentials = req.get_param('base64EncodedCredentials')
        self.auth_basic_addon.credentials_map[domain] = credentials


    def on_delete(self, req, resp, domain):
        """Clears the automatic basic auth settings for a domain.
        ---
        description: Clears Basic Auth for a domain, disabling Automatic Basic Auth for it.
        operationId: clearBasicAuthSettings
        parameters:
            - in: path
              name: domain
              required: true
              schema:
                type: string
              description: The domain for which to clear the basic auth settings
        tags:
            - BrowserUpProxy
        responses:
            204:
                description: The current Basic Authorization setting is cleared and no longer used for requests to a domain.
        """
        self.auth_basic_addon.credentials_map.pop(domain)

class AuthBasicAddOn:

    def __init__(self):
        self.num = 0
        self.credentials_map = {}

    def get_resources(self):
        return [AuthBasicResource(self)]

    def request(self, flow):
        if flow.request.host in self.credentials_map:
            flow.request.headers['Authorization'] = 'Basic ' + self.credentials_map[flow.request.host]
