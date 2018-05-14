"""
TODO: almost everything.
Collect and dumps a python HTTPResponse
as a protobuf blob.
"""
from mitmproxy.utils import data

import sys
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


def loads(blob) -> dummyhttp_pb2.HTTPResponse():
    r = dummyhttp_pb2.HTTPResponse()
    r.ParseFromString(blob)
    return r

