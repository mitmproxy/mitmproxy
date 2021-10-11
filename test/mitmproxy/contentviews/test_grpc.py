import pytest

from mitmproxy.contentviews import grpc
from mitmproxy.contentviews.grpc import ViewGrpcProtobuf, ViewConfig, ProtoParser
from mitmproxy.net.encoding import encode
from mitmproxy.test import tflow, tutils
import struct
from . import full_eval


datadir = "mitmproxy/contentviews/test_grpc_data/"


def helper_pack_grpc_message(data: bytes, compress=False, encoding="gzip") -> bytes:
    if compress:
        data = encode(data, encoding)
    header = struct.pack('!?i', compress, len(data))
    return header + data


custom_parser_rules = [
    ProtoParser.ParserRuleRequest(
        name = "Geo coordinate lookup request",
        # note on flowfilter: for tflow the port gets appended to the URL's host part
        filter = "example\\.com.*/ReverseGeocode",
        field_definitions=[
            ProtoParser.ParserFieldDefinition(tag="1", name="position"),
            ProtoParser.ParserFieldDefinition(tag="1.1", name="latitude", intended_decoding=ProtoParser.DecodedTypes.double),
            ProtoParser.ParserFieldDefinition(tag="1.2", name="longitude", intended_decoding=ProtoParser.DecodedTypes.double),
            ProtoParser.ParserFieldDefinition(tag="3", name="country"),
            ProtoParser.ParserFieldDefinition(tag="7", name="app"),
        ]
    ),
    ProtoParser.ParserRuleResponse(
        name = "Geo coordinate lookup response",
        # note on flowfilter: for tflow the port gets appended to the URL's host part
        filter = "example\\.com.*/ReverseGeocode",
        field_definitions=[
            ProtoParser.ParserFieldDefinition(tag="1.2", name="address"),
            ProtoParser.ParserFieldDefinition(tag="1.3", name="address array element"),
            ProtoParser.ParserFieldDefinition(tag="1.3.1", name="unknown bytes", intended_decoding=ProtoParser.DecodedTypes.bytes),
            ProtoParser.ParserFieldDefinition(tag="1.3.2", name="element value long"),
            ProtoParser.ParserFieldDefinition(tag="1.3.3", name="element value short"),
            ProtoParser.ParserFieldDefinition(tag="", tag_prefixes=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="position"),
            ProtoParser.ParserFieldDefinition(tag=".1", tag_prefixes=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="latitude", intended_decoding=ProtoParser.DecodedTypes.double),  # noqa: E501
            ProtoParser.ParserFieldDefinition(tag=".2", tag_prefixes=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="longitude", intended_decoding=ProtoParser.DecodedTypes.double),  # noqa: E501
            ProtoParser.ParserFieldDefinition(tag="7", name="app"),
        ]
    ),
]

custom_view_config = ViewConfig(
    parser_options=ProtoParser.ParserOptions(exclude_message_headers=True, include_wiretype=True)
)

custom_view_config_parser_rules = ViewConfig(
    parser_rules=custom_parser_rules
)

sim_msg_req = tutils.treq(
    port=443,
    host="example.com",
    path="/ReverseGeocode"
)

sim_msg_resp = tutils.tresp()

sim_flow = tflow.tflow(
    req=sim_msg_req,
    resp=sim_msg_resp
)


def test_view_protobuf(tdata):
    v = full_eval(ViewGrpcProtobuf())
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


def test_view_protobuf_custom_parsing_request(tdata):
    v = full_eval(ViewGrpcProtobuf(custom_view_config_parser_rules))
    p = tdata.path(datadir + "msg1.bin")

    with open(p, "rb") as f:
        raw = f.read()
    view_text, output = v(raw, flow=sim_flow, http_message=sim_flow.request)  # simulate request message
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', 'position   '), ('text', '1    '), ('text', '                               ')],
        [('text', '[double]   '), ('text', 'latitude   '), ('text', '1.1  '), ('text', '38.89816675798073              ')],
        [('text', '[double]   '), ('text', 'longitude  '), ('text', '1.2  '), ('text', '-77.03829828366696             ')],
        [('text', '[string]   '), ('text', 'country    '), ('text', '3    '), ('text', 'de_DE                          ')],
        [('text', '[uint32]   '), ('text', '           '), ('text', '6    '), ('text', '1                              ')],
        [('text', '[string]   '), ('text', 'app        '), ('text', '7    '), ('text', 'de.mcdonalds.mcdonaldsinfoapp  ')]
    ]


def test_view_protobuf_custom_parsing_response(tdata):
    v = full_eval(ViewGrpcProtobuf(custom_view_config_parser_rules))
    p = tdata.path(datadir + "msg3.bin")

    with open(p, "rb") as f:
        raw = f.read()
    view_text, output = v(raw, flow=sim_flow, http_message=sim_flow.response)  # simulate response message
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '                       '), ('text', '1        '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[string]   '), ('text', '                       '), ('text', '1.1      '), ('text', '\x15                                                       ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'address                '), ('text', '1.2      '), ('text', '1650 Pennsylvania Avenue NW, Washington, DC 20502, USA  ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'address array element  '), ('text', '1.3      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', 'unknown bytes          '), ('text', '1.3.1    '), ('text', 'b\'"\'                                                    ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value long     '), ('text', '1.3.2    '), ('text', '1650                                                    ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', '1650                                                    ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'address array element  '), ('text', '1.3      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', 'unknown bytes          '), ('text', '1.3.1    '), ('text', "b'\\x02'                                                 ")],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value long     '), ('text', '1.3.2    '), ('text', 'Pennsylvania Avenue Northwest                           ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', 'Pennsylvania Avenue NW                                  ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'address array element  '), ('text', '1.3      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', 'unknown bytes          '), ('text', '1.3.1    '), ('text', "b'\\x14\\x04'                                             ")],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value long     '), ('text', '1.3.2    '), ('text', 'Northwest Washington                                    ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', 'Northwest Washington                                    ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'address array element  '), ('text', '1.3      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', 'unknown bytes          '), ('text', '1.3.1    '), ('text', "b'\\x0c\\x04'                                             ")],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value long     '), ('text', '1.3.2    '), ('text', 'Washington                                              ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', 'Washington                                              ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'address array element  '), ('text', '1.3      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', 'unknown bytes          '), ('text', '1.3.1    '), ('text', "b'\\x06\\x04'                                             ")],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value long     '), ('text', '1.3.2    '), ('text', 'District of Columbia                                    ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'address array element  '), ('text', '1.3      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', 'unknown bytes          '), ('text', '1.3.1    '), ('text', "b'\\x05\\x04'                                             ")],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value long     '), ('text', '1.3.2    '), ('text', 'USA                                                     ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', 'US                                                      ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'address array element  '), ('text', '1.3      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', 'unknown bytes          '), ('text', '1.3.1    '), ('text', "b'\\x17'                                                 ")],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value long     '), ('text', '1.3.2    '), ('text', '20502                                                   ')],  # noqa: E501
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', '20502                                                   ')],  # noqa: E501
        [('text', '[message]  '), ('text', '                       '), ('text', '1.5      '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'position               '), ('text', '1.5.1    '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'latitude               '), ('text', '1.5.1.1  '), ('text', '38.8970309                                              ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'longitude              '), ('text', '1.5.1.2  '), ('text', '-77.03872559999999                                      ')],  # noqa: E501
        [('text', '[uint32]   '), ('text', '                       '), ('text', '1.5.2    '), ('text', '1                                                       ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'position               '), ('text', '1.5.3    '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'latitude               '), ('text', '1.5.3.1  '), ('text', '38.8962271697085                                        ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'longitude              '), ('text', '1.5.3.2  '), ('text', '-77.0400511802915                                       ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'position               '), ('text', '1.5.4    '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'latitude               '), ('text', '1.5.4.1  '), ('text', '38.8989251302915                                        ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'longitude              '), ('text', '1.5.4.2  '), ('text', '-77.03735321970849                                      ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'position               '), ('text', '1.5.5    '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'latitude               '), ('text', '1.5.5.1  '), ('text', '38.896898                                               ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'longitude              '), ('text', '1.5.5.2  '), ('text', '-77.03917229999999                                      ')],  # noqa: E501
        [('text', '[message]  '), ('text', 'position               '), ('text', '1.5.6    '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'latitude               '), ('text', '1.5.6.1  '), ('text', '38.8982543                                              ')],  # noqa: E501
        [('text', '[double]   '), ('text', 'longitude              '), ('text', '1.5.6.2  '), ('text', '-77.0382321                                             ')],  # noqa: E501
        [('text', '[string]   '), ('text', '                       '), ('text', '1.7      '), ('text', 'ChIJAXiAory3t4kRpkrvas9dYmQ                             ')],  # noqa: E501
        [('text', '[message]  '), ('text', '                       '), ('text', '2        '), ('text', '                                                        ')],  # noqa: E501
        [('text', '[uint32]   '), ('text', '                       '), ('text', '2.1      '), ('text', '21                                                      ')],  # noqa: E501
    ]


def test_view_protobuf_custom_config(tdata):
    v = full_eval(ViewGrpcProtobuf(custom_view_config))
    p = tdata.path(datadir + "msg1.bin")

    with open(p, "rb") as f:
        raw = f.read()
    view_text, output = v(raw)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[bit_64->fixed64]        '), ('text', '  '), ('text', '1.1  '), ('text', '4630671247600644312            ')],
        [('text', '[bit_64->fixed64]        '), ('text', '  '), ('text', '1.2  '), ('text', '13858493542095451628           ')],
        [('text', '[len_delimited->string]  '), ('text', '  '), ('text', '3    '), ('text', 'de_DE                          ')],
        [('text', '[varint->uint32]         '), ('text', '  '), ('text', '6    '), ('text', '1                              ')],
        [('text', '[len_delimited->string]  '), ('text', '  '), ('text', '7    '), ('text', 'de.mcdonalds.mcdonaldsinfoapp  ')]
    ]


def test_view_grpc(tdata):
    v = full_eval(ViewGrpcProtobuf())
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


def test_view_grpc_compressed(tdata):
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


def test_render_priority():
    v = grpc.ViewGrpcProtobuf()
    assert v.render_priority(b"data", content_type="application/x-protobuf")
    assert v.render_priority(b"data", content_type="application/x-protobuffer")
    assert v.render_priority(b"data", content_type="application/grpc-proto")
    assert v.render_priority(b"data", content_type="application/grpc")
    assert not v.render_priority(b"data", content_type="text/plain")
