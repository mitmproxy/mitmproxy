import pytest

from mitmproxy.contentviews import grpc
from mitmproxy.net.encoding import encode
import struct
from . import full_eval


datadir = "mitmproxy/contentviews/test_grpc_data/"


def helper_pack_grpc_message(data: bytes, compress=False, encoding="gzip") -> bytes:
    if compress:
        data = encode(data, encoding)
    header = struct.pack('!?i', compress, len(data))
    return header + data


custom_parser_config = grpc.ViewConfig(
    parser_options=grpc.ProtoParser.ParserOptions(exclude_message_headers=True, include_wiretype=True)
)


def test_view_protobuf(tdata):
    v = full_eval(grpc.ViewGrpcProtobuf())
    p = tdata.path(datadir + "msg1.bin")

    with open(p, "rb") as f:
        raw = f.read()
    view_text, output = v(raw)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '  '), ('text', '1    '), ('text', '                               ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.1  '), ('text', '4630671247600644312            ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.2  '), ('text', '13858493542095451628           ')],
        [('text', '[string]   '), ('text', '  '), ('text', '3    '), ('text', 'de_DE                          ')],
        [('text', '[uint32]   '), ('text', '  '), ('text', '6    '), ('text', '1                              ')],
        [('text', '[string]   '), ('text', '  '), ('text', '7    '), ('text', 'de.mcdonalds.mcdonaldsinfoapp  ')]
    ]
    with pytest.raises(ValueError, match='not a valid protobuf message'):
        v(b'foobar')


def test_view_protobuf_custom_config(tdata):
    v = full_eval(grpc.ViewGrpcProtobuf(custom_parser_config))
    p = tdata.path(datadir + "msg1.bin")

    with open(p, "rb") as f:
        raw = f.read()
    view_text, output = v(raw)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    print(output)
    assert output == [
        [('text', '[bit_64->fixed64]        '), ('text', '  '), ('text', '1.1  '), ('text', '4630671247600644312            ')],
        [('text', '[bit_64->fixed64]        '), ('text', '  '), ('text', '1.2  '), ('text', '13858493542095451628           ')],
        [('text', '[len_delimited->string]  '), ('text', '  '), ('text', '3    '), ('text', 'de_DE                          ')],
        [('text', '[varint->uint32]         '), ('text', '  '), ('text', '6    '), ('text', '1                              ')],
        [('text', '[len_delimited->string]  '), ('text', '  '), ('text', '7    '), ('text', 'de.mcdonalds.mcdonaldsinfoapp  ')]
    ]
    with pytest.raises(ValueError, match='not a valid protobuf message'):
        v(b'foobar')


def test_view_grpc(tdata):
    v = full_eval(grpc.ViewGrpcProtobuf())
    p = tdata.path(datadir + "msg1.bin")

    with open(p, "rb") as f:
        raw = f.read()
        # pack into protobuf message
        raw = helper_pack_grpc_message(raw)

    view_text, output = v(raw, content_type="application/grpc")
    assert view_text == "gRPC"
    output = list(output)  # assure list conversion if generator

    assert output == [
        [('text', 'gRPC message 0 (compressed False)')],
        [('text', '[message]  '), ('text', '  '), ('text', '1    '), ('text', '                               ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.1  '), ('text', '4630671247600644312            ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.2  '), ('text', '13858493542095451628           ')],
        [('text', '[string]   '), ('text', '  '), ('text', '3    '), ('text', 'de_DE                          ')],
        [('text', '[uint32]   '), ('text', '  '), ('text', '6    '), ('text', '1                              ')],
        [('text', '[string]   '), ('text', '  '), ('text', '7    '), ('text', 'de.mcdonalds.mcdonaldsinfoapp  ')]
    ]


def test_view_grpc_compresses(tdata):
    v = full_eval(grpc.ViewGrpcProtobuf())
    p = tdata.path(datadir + "msg1.bin")

    with open(p, "rb") as f:
        raw = f.read()
        # pack into protobuf message
        raw = helper_pack_grpc_message(raw, True, "gzip")

    view_text, output = v(raw, content_type="application/grpc")
    assert view_text == "gRPC"
    output = list(output)  # assure list conversion if generator

    assert output == [
        [('text', 'gRPC message 0 (compressed gzip)')],
        [('text', '[message]  '), ('text', '  '), ('text', '1    '), ('text', '                               ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.1  '), ('text', '4630671247600644312            ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.2  '), ('text', '13858493542095451628           ')],
        [('text', '[string]   '), ('text', '  '), ('text', '3    '), ('text', 'de_DE                          ')],
        [('text', '[uint32]   '), ('text', '  '), ('text', '6    '), ('text', '1                              ')],
        [('text', '[string]   '), ('text', '  '), ('text', '7    '), ('text', 'de.mcdonalds.mcdonaldsinfoapp  ')]
    ]


# @pytest.mark.parametrize("filename", ["protobuf02.bin", "protobuf03.bin"])
# def test_format_pbuf(filename, tdata):
#     path = tdata.path(datadir + filename)
#     with open(path, "rb") as f:
#         input = f.read()
#     with open(path.replace(".bin", "-decoded.bin")) as f:
#         expected = f.read()

#     assert protobuf.format_pbuf(input) == expected


def test_render_priority():
    v = grpc.ViewGrpcProtobuf()
    assert v.render_priority(b"data", content_type="application/x-protobuf")
    assert v.render_priority(b"data", content_type="application/x-protobuffer")
    assert v.render_priority(b"data", content_type="application/grpc-proto")
    assert v.render_priority(b"data", content_type="application/grpc")
    assert not v.render_priority(b"data", content_type="text/plain")
