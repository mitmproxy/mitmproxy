from urllib.parse import urlparse
from mitmproxy import ctx
from marshmallow import Schema, fields

import re

DEFAULT_PAGE_REF = "Default"
DEFAULT_PAGE_TITLE = "Default"

class URLRewriteRule(Schema):
    url_pattern = fields.Str(optional=True, description="Regular expression pattern to replace")
    replace_with = fields.Str(required=True,  description="String to replace pattern matches with ")

class RewriteUrlResource:

    def addon_path(self):
        return "rewrite_url"

    def apispec(self, spec):
        spec.components.schema('URLRewriteRule', schema=URLRewriteRule)
        spec.path(resource=self)

    def __init__(self, rewrite_url_addon):
        self.rewrite_url_addon = rewrite_url_addon
        for a in ctx.master.addons.get("scriptloader").addons:
            if 'har_capture.py' in a.fullpath:
                self.rewrite_url_addon.har_dump_addon = a.addons[0].addons[0]

    def on_put(self, req, resp):
        """Set URL rewrite  rules
        ---
        description: Sets rewrite rules
        operationId: setURLRewriteRules
        tags:
            - BrowserUpProxy
        requestBody:
            content:
              application/json:
                 type: array
                 items:
                    schema:
                        $ref: "#/components/schemas/URLRewriteRule"
        responses:
            204:
                description: Success!
        """
        for k, v in req.params.items():
            compiled_pattern = self.parse_regexp(k)
            self.rewrite_url_addon.rules[k] = {
                "replacement": v,
                "url_pattern": compiled_pattern
            }


    def on_delete(self, req, resp):
        """Clear URL rewrite  rules
        ---
        description: Clear URL rewrite rules
        operationId: clearURLRewriteRules
        tags:
            - Rewrite
        responses:
            204:
                description: Success!
        """
        self.rewrite_url_addon.rules = {}

    def parse_regexp(self, raw_regexp):
        if not raw_regexp.startswith('^'):
            raw_regexp = '^' + raw_regexp
        if not raw_regexp.endswith('$'):
            raw_regexp = raw_regexp + '$'
        return re.compile(raw_regexp)


class RewriteUrlAddOn:

    def __init__(self):
        self.har_dump_addon = None
        self.rules = {}

    def get_resources(self):
        return [RewriteUrlResource(self)]

    def request(self, flow):
        self.har_dump_addon.get_or_create_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE, True)
        rewrote = False
        rewritten_url = flow.request.url
        for url, rule in self.rules.items():
            if rule['url_pattern'].match(rewritten_url):
                rewrote = True
                rewritten_url = re.sub(rule['url_pattern'], rule['replacement'], rewritten_url)

        if rewrote:
            original_host_port = flow.request.host + ':' + str(flow.request.port)

            parsed_rewritten_url = urlparse(rewritten_url)
            rewritten_host_port = parsed_rewritten_url.hostname + ':' + str(parsed_rewritten_url.port)

            flow.request.url = rewritten_url

            if original_host_port is not rewritten_host_port:
                if 'Host' in flow.request.headers:
                    flow.request.headers['Host'] = rewritten_host_port



    def is_http_or_https(self, req):
        return req.url.startswith('https') or req.url.startswith('http')

addons = [
    RewriteUrlAddOn()
]