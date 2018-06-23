from mitmproxy.io import protobuf


def response(f):
    protobuf.loads(protobuf.dumps(f))
