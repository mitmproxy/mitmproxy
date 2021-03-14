import re
import falcon

from mitmproxy import http
from marshmallow import Schema, fields

class AllowListSchema(Schema):
    url_pattern = fields.Str(required=True,description="URL Regex Pattern to match")
    status_code = fields.Str(required=True,description="HTTP Status Code to match")

class AllowListResource:

    def apispec(self, spec):
        spec.components.schema('AllowList', schema=AllowListSchema)
        spec.path(resource=self)

    def addon_path(self):
        return "allowlist"

    def __init__(self, allow_list_addon):
        self.allow_list_addon = allow_list_addon

    def on_get(self, req, resp):
        """Get the AllowList.
        ---
        description: Get an AllowList
        operationId: getAllowList
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: The current allowlist. Only allowed requests will pass through.
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/AllowList"
        """

    def on_post(self, req, resp):
        """Posts the AllowList.
        ---
        description: Sets an AllowList
        operationId: setAllowList
        tags:
            - BrowserUpProxy
        requestBody:
            content:
              application/json:
                schema:
                    $ref: "#/components/schemas/AllowList"
        responses:
            204:
                description: Success!
        """
        raw_url_patterns = req.get_param('urlPatterns')
        status_code = req.get_param('statusCode')

        try:
            self.allow_list_addon.set_allow_list(status_code, raw_url_patterns)
        except re.error:
            raise falcon.HTTPBadRequest("Invalid regexp patterns")

    def on_delete(self, req, resp):
        """Clear the AllowList.
        ---
        description: Clears the AllowList, which will turn-off allowlist based filtering
        operationId: clearAllowList
        tags:
            - BrowserUpProxy
        responses:
            204:
                description: The allowlist was cleared and allowlist-based filtering is OFF until a new list is posted.
        """
        self.allow_list_addon.allow_list = None

class AllowListAddOn:

    def __init__(self):
        self.num = 0
        self.allow_list = None

    def __parse_regexp(self, raw_regexp):
        if not raw_regexp.startswith('^'):
            raw_regexp = '^' + raw_regexp
        if not raw_regexp.endswith('$'):
            raw_regexp = raw_regexp + '$'
        return re.compile(raw_regexp)

    def set_allowlist(self, status_code, allowlist_pattern_str):
        url_patterns = allowlist_pattern_str.strip("[]").split(",")
        url_patterns_compiled = []
        for raw_pattern in url_patterns:
            url_patterns_compiled.append(self.__parse_regexp(raw_pattern))

    def get_resources(self):
        return [AllowListResource(self)]

    def allowlist_enabled(self):
        return (self.allow_list is not None)

    def request(self, flow):
        if not self.allowlist_enabled():
            return

        is_allowlisted = False
        for up in self.allow_list['url_patterns']:
            if up.match(flow.request.url):
                is_allowlisted = True
                break

        if not is_allowlisted:
            flow.response = http.HTTPResponse.make(
                int(self.allow_list['status_code']),
                b"",
                {"Content-Type": "text/html"}
            )
            flow.metadata['AllowListFiltered'] = True

addons = [
    AllowListAddOn()
]