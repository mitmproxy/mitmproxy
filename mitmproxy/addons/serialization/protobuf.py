import sys

from mitmproxy.utils import data
sys.path.extend([data.pkg_data.path("addons/serialization")])
from mitmproxy.addons.serialization import dummyhttp_pb2


def dumps(state : dict) -> bytes:
    """
    Just fill and dump the dummy structure.
    """
    r = dummyhttp_pb2.HTTPResponse()
    r.request.method = getattr(r.request, state['request']['method'].decode())
    for attr in ['host', 'port', 'path']:
        if attr in state['request']:
            setattr(r.request, attr, state['request'][attr])
    for attr in ['status_code', 'content']:
        if attr in state['response']:
            setattr(r, attr, state['response'][attr])
    return r.SerializeToString()


def dump(state: dict, session) -> int:
    r = dumps(state)
    mid = session.store(r)
    return mid


def loads(blob) -> dummyhttp_pb2.HTTPResponse():
    r = dummyhttp_pb2.HTTPResponse()
    r.ParseFromString(blob)
    return r


def load(mid, session) -> bytes:
    r = dummyhttp_pb2.HTTPResponse()
    blob = session.collect(mid)
    r.ParseFromString(blob)
    return r