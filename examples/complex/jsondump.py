import base64
import json

from mitmproxy import ctx


class JSONDumper:
    def __init__(self):
        self.outfile = open('jsondump.out', 'a')
        self.transformations = None

    def __del__(self):
        if self.outfile:
            self.outfile.close()

    fields = {
        'timestamp': (
            ('error', 'timestamp'),

            ('request', 'timestamp_start'),
            ('request', 'timestamp_end'),

            ('response', 'timestamp_start'),
            ('response', 'timestamp_end'),

            ('client_conn', 'timestamp_start'),
            ('client_conn', 'timestamp_end'),
            ('client_conn', 'timestamp_tls_setup'),

            ('server_conn', 'timestamp_start'),
            ('server_conn', 'timestamp_end'),
            ('server_conn', 'timestamp_tls_setup'),
            ('server_conn', 'timestamp_tcp_setup'),
        ),
        'ip': (
            ('server_conn', 'source_address'),
            ('server_conn', 'ip_address'),
            ('server_conn', 'address'),
            ('client_conn', 'address'),
        ),
        'ws_messages': (
            ('messages', ),
        ),
        'headers': (
            ('request', 'headers'),
            ('response', 'headers'),
        ),
    }

    def _init_transformations(self):
        self.transformations = [
            {
                'fields': self.fields['headers'],
                'func': dict,
            },
            {
                'fields': self.fields['timestamp'],
                'func': lambda t: int(t * 1000),
            },
            {
                'fields': self.fields['ip'],
                'func': lambda addr: {
                    'host': addr[0].replace('::ffff:', ''),
                    'port': addr[1],
                },
            },
            {
                'fields': self.fields['ws_messages'],
                'func': lambda ms: [{
                    'type':        m[0],
                    'from_client': m[1],
                    'content':     m[2],
                    'timestamp':   int(m[3] * 1000),
                } for m in ms],
            }
        ]

    @staticmethod
    def transform_field(obj, path, func):
        """
        Apply a transformation function `func` to a value
        under the specified `path` in the `obj` dictionary.
        """
        for key in path[:-1]:
            if not (key in obj and obj[key]):
                return
            obj = obj[key]
        if path[-1] in obj and obj[path[-1]]:
            obj[path[-1]] = func(obj[path[-1]])

    @classmethod
    def convert_to_strings(cls, obj):
        """
        Recursively convert all list/dict elements of type `bytes` into strings.
        """
        if isinstance(obj, dict):
            return {cls.convert_to_strings(key): cls.convert_to_strings(value)
                    for key, value in obj.items()}
        elif isinstance(obj, list):
            return [cls.convert_to_strings(element) for element in obj]
        elif isinstance(obj, bytes):
            return str(obj)[2:-1]
        return obj

    def dump(self, frame):
        for tfm in self.transformations:
            for field in tfm['fields']:
                self.transform_field(frame, field, tfm['func'])
        frame = json.dumps(self.convert_to_strings(frame))

        self.outfile.write(frame+"\n")

    def configure(self, _):
        self._init_transformations()

    def response(self, flow):
        self.dump(flow.get_state())

    def error(self, flow):
        self.dump(flow.get_state())

    def websocket_messages(self, flow):
        self.dump(flow.get_state())

    def websocket_error(self, flow):
        self.dump(flow.get_state())

addons = [JSONDumper()]
