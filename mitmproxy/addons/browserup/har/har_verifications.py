import re
from glom import glom
import json
from jsonschema import validate
from jsonschema import ValidationError
from jsonpath_ng import parse


class HarVerifications:

    def __init__(self, har):
        self.har = har

    def rmatch(self, val, str_rxp):
        if val is None:
            return False
        if isinstance(val, bytes):
            val = str(val, "utf-8")
        return re.search(str_rxp, val, flags=re.IGNORECASE)

    def rmatch_any(self, items, rxp):
        if items is None or len(items) == 0 or rxp is None:
            return False

        for item in items:
            if isinstance(item, bytes):
                item = str(item, "utf-8")
            if self.rmatch(item, rxp):
                return True
        return False

    def rmatch_key_val(self, items, kv):
        name = True
        value = True

        if items is None or len(items) == 0 or kv is None:
            return False

        for item in items:
            if 'name' in kv:
                name = self.rmatch(item['name'], kv['name'])

            if 'value' in kv:
                value = self.rmatch(kv['value'], item['value'])

            if name and value:
                return True

        return False

    def schema_validate(self, item, schema):
        try:
            if isinstance(item, str):
                item = json.loads(item)
            validate(instance=item, schema=schema)
        except (ValidationError, ValueError):
            return False
        return True

    def valid_json(self, item):
        if item is None:
            return False
        try:
            json.loads(item)
        except ValueError:
            return False
        return True

    def has_json_path(self, json_str, json_path):
        if self.valid_json(json_str) is False:
            return False
        jsonpath_expr = parse(json_path)
        matches = jsonpath_expr.find(json.loads(json_str))
        return len(matches) > 0

    def current_page(self):
        return self.har['log']['pages'][-1]['id']

    def no_entries(self):
        (self.har['log']['entries'] is None) or (len(self.har['log']['entries']) == 0)

    def entries(self, criteria=False):
        # Use glom to dig into the har entries, responses and websockets to get down to an array of something or others
        # (headers, websocket messages, content then we execute our test against that item
        # current, *, or filter
        entry_list = self.har['log']['entries']
        har_entry_filters = {
            'page': (lambda item, pgref: glom(item, 'pageref', default='') == pgref),

            'status': (lambda item, status: self.rmatch(str(glom(item, 'response.status', default=None)), status)),
            'url': (lambda item, url_rxp: self.rmatch(str(glom(item, 'request.url', default=None)), url_rxp)),
            'content': (lambda item, content_rxp: self.rmatch(str(glom(item, 'response.content.text', default=None)), content_rxp)),
            'content_type': (lambda item, content_type_rxp: self.rmatch(str(glom(item, 'response.content.mimeType', default=None)),
                             content_type_rxp)),
            'request_header': (lambda item, match_rgxp: self.rmatch_key_val(glom(item, 'request.headers', default=[]), match_rgxp)),
            'response_header': (lambda item, match_rgxp: self.rmatch_key_val(glom(item, 'response.headers', default=[]), match_rgxp)),
            'request_cookie': (lambda item, match_rgxp: self.rmatch_key_val(glom(item, 'request.cookies', default=[]), match_rgxp)),
            'response_cookie': (lambda item, match_rgxp: self.rmatch_key_val(glom(item, 'response.cookies', default=[]), match_rgxp)),
            'websocket_message': (lambda item, ws_rxp: self.rmatch_any(glom(item, ('_webSocketMessages', ['data']), default=[]), ws_rxp)),
            'json_valid': (lambda item, _: self.valid_json(str(glom(item, 'response.content.text', default=None)))),
            'json_path': (lambda item, path: self.has_json_path(str(glom(item, 'response.content.text', default=None)), path)),
            'json_schema': (lambda item, schema: self.schema_validate(str(glom(item, 'response.content.text', default=None)), schema)),
        }

        for filter_name, target_value in criteria.items():
            filter_lambda = har_entry_filters.get(filter_name, None)
            if filter_lambda is not None:
                if filter_name == 'page' and target_value == 'current':
                    target_value = self.current_page()
                entry_list = [entry for entry in entry_list if filter_lambda(entry, target_value)]

        return entry_list

    def gsize(self, item, path):
        return self.not_neg(glom(item, 'request.headersSize', default=0))

    def not_neg(self, val):
        val = int(val)
        return 0 if val == -1 or val is None else val

    def measure(self, items, measurement):
        measurements = {
            'request_headers': (lambda item: self.gsize(item, 'request.headersSize')),
            'response_headers': (lambda item: self.gsize(item, 'response.headersSize')),
            'request_body': (lambda item: self.gsize(item, 'request.bodySize')),
            'response_body': (lambda item: self.gsize(item, 'request.bodySize')),
            'request': (lambda item: self.gsize(item, 'request.bodySize') + self.gsize(item, 'request.headerSize')),
            'response': (lambda item: self.gsize(item, 'response.bodySize') + self.gsize(item, 'response.headerSize')),
            'time': (lambda item: self.gsize(item, 'time')),
        }
        method = measurements[measurement]
        return list(map(method, items))

    def present(self, criteria):
        return len(self.entries(criteria)) > 0

    def not_present(self, criteria):
        return len(self.entries(criteria)) == 0

    def get_max(self, criteria, measurement_name):
        items = self.entries(criteria)
        return max(self.measure(items, measurement_name), default=0)

    def get_sum(self, criteria, measurement_name):
        items = self.entries(criteria)
        return sum(self.measure(items, measurement_name))
