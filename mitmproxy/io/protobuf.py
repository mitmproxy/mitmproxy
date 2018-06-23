from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.io.proto import http_pb2


def dumps(f: flow.Flow) -> bytes:
    if f.type != "http":
        raise exceptions.TypeError("Flow types different than HTTP not supported yet!")
    else:
        hf = http_pb2.HTTPFlow()
        state = f.get_state()
        for r in ['request', 'response']:
            for field in state[r]:
                if hasattr(getattr(hf, r), field) and state[r][field] is not None:
                    if field == 'headers':
                        for n, v in state[r][field]:
                            header = (getattr(hf, r)).headers.add()
                            header.name = n
                            header.value = v
                    else:
                        setattr(getattr(hf, r), field, state[r][field])
        if state['error']:
            hf.error.msg = state['error']['msg']
            hf.error.timestamp = state['error']['timestamp']
        for c in ['client_conn', 'server_conn']:
            for field in state[c]:
                if hasattr(getattr(hf, c), field) and state[c][field] is not None:
                    if field in ['address', 'ip_address', 'source_address']:
                        getattr(getattr(hf, c), field).host = state[c][field][0]
                        getattr(getattr(hf, c), field).port = state[c][field][1]
                    else:
                        setattr(getattr(hf, c), field, state[c][field])
        for val in ['intercepted', 'marked', 'mode', 'id', 'version']:
            if state[val] is not None:
                setattr(hf, val, state[val])
    return hf.SerializeToString()


def loads(blob: bytes) -> flow.Flow:
    r = http_pb2.HTTPFlow()
    state = dict()
    r.ParseFromString(blob)
    _dump_object(r, state)


def _dump_object(obj, d):
    for descriptor in obj.DESCRIPTOR.fields:
        value = getattr(obj, descriptor.name)
        if descriptor.type == descriptor.TYPE_MESSAGE:
            d[descriptor.name] = {}
            if descriptor.label == descriptor.LABEL_REPEATED:
                [_dump_object(v, d[descriptor.name]) for v in value]
            else:
                _dump_object(value, d[descriptor.name])
        elif descriptor.type == descriptor.TYPE_ENUM:
            enum_name = descriptor.enum_type.values[value].name
            d[descriptor.name] = enum_name
        else:
            d[descriptor.name] = value
