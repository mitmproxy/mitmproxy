import json
import re
import asyncio
import falcon

from mitmproxy import ctx
from mitmproxy import http

class BlockListResource:

    def addon_path(self):
        return "blocklist"

    def __init__(self, block_list_addon):
        self.block_list_addon = block_list_addon

    def on_get(self, req, resp, method_name):
        try:
            asyncio.get_event_loop()
        except:
            asyncio.set_event_loop(asyncio.new_event_loop())
        getattr(self, "on_" + method_name)(req, resp)

    def on_put(self, req, resp, method_name):
        try:
            asyncio.get_event_loop()
        except:
            asyncio.set_event_loop(asyncio.new_event_loop())
        getattr(self, "on_" + method_name)(req, resp)

    def on_blocklist_requests(self, req, resp):
        url_pattern = req.get_param('urlPattern')
        status_code = req.get_param('statusCode')
        http_method_pattern = req.get_param('httpMethodPattern')

        ctx.log.info(
            'Blocklisting url pattern: {}, status code: {}, method pattern: {}'.
                format(url_pattern, status_code, http_method_pattern))

        try:
            url_pattern_compiled = self.parse_regexp(url_pattern)

            http_method_pattern_compiled = None
            if http_method_pattern is not None:
                http_method_pattern_compiled = self.parse_regexp(http_method_pattern)
        except re.error:
            raise falcon.HTTPBadRequest("Invalid regexp patterns")

        self.block_list_addon.block_list.append({
            "status_code": status_code,
            "url_pattern": url_pattern_compiled,
            "http_method_pattern": http_method_pattern_compiled
        })

    def on_set_block_list(self, req, resp):
        self.block_list_addon.block_list = []

        blocklist = json.loads(req.bounded_stream.read())

        for bl_item in blocklist:
            try:
                url_pattern_compiled = self.parse_regexp(bl_item['urlPattern'])

                http_method_pattern_compiled = None
                if bl_item['httpMethodPattern'] is not None:
                    http_method_pattern_compiled = self.parse_regexp(bl_item['httpMethodPattern'])

                ctx.log.info(
                    'Blocklisting url pattern: {}, status code: {}, method pattern: {}'.
                        format(bl_item['urlPattern'], bl_item['statusCode'], bl_item['httpMethodPattern']))

                self.block_list_addon.block_list.append({
                    "status_code": bl_item['statusCode'],
                    "url_pattern": url_pattern_compiled,
                    "http_method_pattern": http_method_pattern_compiled
                })
            except re.error:
                raise falcon.HTTPBadRequest("Invalid regexp patterns")

    def parse_regexp(self, raw_regexp):
        if not raw_regexp.startswith('^'):
            raw_regexp = '^' + raw_regexp
        if not raw_regexp.endswith('$'):
            raw_regexp = raw_regexp + '$'
        return re.compile(raw_regexp)

class BlockListAddOn:

    def __init__(self):
        self.num = 0
        self.block_list = []

    def get_resource(self):
        return BlockListResource(self)

    def is_blocklist_enabled(self):
        return len(self.block_list) > 0

    def http_connect(self, flow):
        if not self.is_blocklist_enabled():
            return

        is_blocklisted = False
        status_code = 400

        for bl_item in self.block_list:
            request_url = flow.request.url

            if bl_item['http_method_pattern'] is None:
                break

            if not request_url.startswith("http") and not request_url.startswith("https"):
                request_url = 'https://' + request_url

            if bl_item['url_pattern'].match(request_url) and \
                    ((bl_item['http_method_pattern'] is None) or
                     (bl_item['http_method_pattern'].match(flow.request.method))):
                status_code = bl_item['status_code']
                is_blocklisted = True
                break

        if is_blocklisted:
            flow.response = http.HTTPResponse.make(
                int(status_code),
                b"",
                {"Content-Type": "text/html"}
            )
            flow.metadata['BlockListFiltered'] = True

    def request(self, flow):
        if not self.is_blocklist_enabled():
            return

        is_blocklisted = False
        status_code = 400

        for bl_item in self.block_list:
            request_url = flow.request.url

            if flow.request.method == 'CONNECT':
                if bl_item['http_method_pattern'] is None:
                    break

                if not request_url.startswith("http") and not request_url.startswith("https"):
                    request_url = 'https://' + request_url

            if bl_item['url_pattern'].match(request_url) and \
                    ((bl_item['http_method_pattern'] is None) or
                     (bl_item['http_method_pattern'].match(flow.request.method))):
                status_code = bl_item['status_code']
                is_blocklisted = True
                break

        if is_blocklisted:
            flow.response = http.HTTPResponse.make(
                int(status_code),
                b"",
                {"Content-Type": "text/html"}
            )
            flow.metadata['BlockListFiltered'] = True

addons = [
    BlockListAddOn()
]