from mitmproxy.contentviews import grpc


def test_render_priority():
    v = grpc.ViewGrpcProtobuf()
    assert v.render_priority(b"data", content_type="application/x-protobuf")
    assert v.render_priority(b"data", content_type="application/x-protobuffer")
    assert v.render_priority(b"data", content_type="application/grpc-proto")
    assert v.render_priority(b"data", content_type="application/grpc")
    assert not v.render_priority(b"data", content_type="text/plain")
