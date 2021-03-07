"""
This inline script can be used to dump flows as HAR files.

example cmdline invocation:
mitmdump -s ./har_dump.py --set hardump=./dump.har

filename endwith '.zhar' will be compressed:
mitmdump -s ./har_dump.py --set hardump=./dump.zhar
"""

import json
import base64
import typing
import tempfile

import re
import falcon

from mitmproxy import ctx
from mitmproxy import connections
from mitmproxy import version
from mitmproxy.utils import strutils
from mitmproxy.net.http import cookies
from mitmproxy import http


class AllowListResource:

    def addon_path(self):
        return "allowlist"

    def __init__(self, allow_list_addon):
        self.allow_list_addon = allow_list_addon

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)

    def on_allowlist_requests(self, req, resp):
        raw_url_patterns = req.get_param('urlPatterns')
        status_code = req.get_param('statusCode')

        url_patterns = raw_url_patterns.strip("[]").split(",")
        url_patterns_compiled = []

        try:
            for raw_pattern in url_patterns:
                url_patterns_compiled.append(self.parse_regexp(raw_pattern))
        except re.error:
            raise falcon.HTTPBadRequest("Invalid regexp patterns")

        self.allow_list_addon.allow_list = {
            "status_code": status_code,
            "url_patterns": url_patterns_compiled
        }

    def on_add_allowlist_pattern(self, req, resp):
        url_pattern = req.get_param('urlPattern')

        if not hasattr(self.allow_list_addon.allow_list, "status_code") \
                or not hasattr(self.allow_list_addon.allow_list, "url_patterns"):
            raise falcon.HTTPBadRequest("Allowlist is disabled. Cannot add patterns to a disabled allowlist.")

        self.allow_list_addon.allow_list["url_patterns"].append(url_pattern)

    def on_enable_empty_allowlist(self, req, resp):
        status_code = req.get_param('statusCode')

        self.allow_list_addon.allow_list["url_patterns"] = []
        self.allow_list_addon.allow_list["status_code"] = status_code

    def on_disable_allowlist(self, req, resp):
        self.allow_list_addon.allow_list = {}

    def parse_regexp(self, raw_regexp):
        if not raw_regexp.startswith('^'):
            raw_regexp = '^' + raw_regexp
        if not raw_regexp.endswith('$'):
            raw_regexp = raw_regexp + '$'
        return re.compile(raw_regexp)

class AllowListAddOn:

    def __init__(self):
        self.num = 0
        self.allow_list = {}

    def get_resource(self):
        return AllowListResource(self)

    def is_allowlist_enabled(self):
        if 'status_code' in self.allow_list and 'url_patterns' in self.allow_list:
            return True
        return False

    def request(self, flow):
        if not self.is_allowlist_enabled():
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