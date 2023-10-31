import struct

import pytest

from . import full_eval
from mitmproxy.contentviews import grpc
from mitmproxy.contentviews.grpc import parse_grpc_messages
from mitmproxy.contentviews.grpc import ProtoParser
from mitmproxy.contentviews.grpc import ViewConfig
from mitmproxy.contentviews.grpc import ViewGrpcProtobuf
from mitmproxy.net.encoding import encode
from mitmproxy.test import tflow
from mitmproxy.test import tutils

datadir = "mitmproxy/contentviews/test_grpc_data/"


def helper_pack_grpc_message(data: bytes, compress=False, encoding="gzip") -> bytes:
    if compress:
        data = encode(data, encoding)
    header = struct.pack("!?i", compress, len(data))
    return header + data


# fmt: off
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
sim_msg_req.headers["grpc-encoding"] = "gzip"
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
    # expect to parse 1.3.2 and 1.3.3 as string automatically
    # even if there is a length delimeted field containing `b"DC"`, which would translate to
    # two deprecated fields [8: group_start, 8: group_end] (and thus represent a valid nested message,
    # but containing deprecated wire types)
    custom_view_config_parser_rules.parser_rules[1].field_definitions[3].intended_decoding = None
    custom_view_config_parser_rules.parser_rules[1].field_definitions[4].intended_decoding = None

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
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', 'DC                                                      ')],  # noqa: E501
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


def test_view_protobuf_custom_parsing_response2(tdata):
    # try to parse 1.3.2 and 1.3.3 as string
    custom_view_config_parser_rules.parser_rules[1].field_definitions[3].intended_decoding = ProtoParser.DecodedTypes.string  # 1.3.2
    custom_view_config_parser_rules.parser_rules[1].field_definitions[4].intended_decoding = ProtoParser.DecodedTypes.string  # 1.3.3

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
        [('text', '[string]   '), ('text', 'element value short    '), ('text', '1.3.3    '), ('text', 'DC                                                      ')],  # noqa: E501
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

    view_text, output = v(raw, content_type="application/grpc", http_message=sim_msg_req)
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
    with pytest.raises(ValueError, match='invalid gRPC message'):
        v(b'foobar', content_type="application/grpc")
    with pytest.raises(ValueError, match='Failed to decompress gRPC message with gzip'):
        list(parse_grpc_messages(data=b'\x01\x00\x00\x00\x01foobar', compression_scheme="gzip"))


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


def helper_encode_base128le(val: int):
    # hacky base128le encoding
    if val <= 0:
        return b'\x00'
    res = []
    while val > 0:
        part = val & 0b1111111
        val = val >> 7
        if val > 0:
            res.append(part + 0x80)
        else:
            res.append(part)
    return bytes(res)


def helper_gen_varint_msg_field(f_idx: int, f_val: int):
    # manual encoding of protobuf data
    f_wt = 0  # field type 0 (varint)
    tag = (f_idx << 3) | f_wt  # combined tag
    msg = helper_encode_base128le(tag)  # add encoded tag to message
    msg = msg + helper_encode_base128le(f_val)  # add varint encoded field value
    return msg


def helper_gen_bits32_msg_field(f_idx: int, f_val: int):
    # manual encoding of protobuf data
    f_wt = 5  # field type 5 (bits32)
    tag = (f_idx << 3) | f_wt  # combined tag
    msg = helper_encode_base128le(tag)  # add encoded tag to message
    msg = msg + struct.pack("<I", f_val)  # add varint encoded field value
    return msg


def helper_gen_bits64_msg_field(f_idx: int, f_val: int):
    # manual encoding of protobuf data
    f_wt = 1  # field type 1 (bits64)
    tag = (f_idx << 3) | f_wt  # combined tag
    msg = helper_encode_base128le(tag)  # add encoded tag to message
    msg = msg + struct.pack("<Q", f_val)  # add varint encoded field value
    return msg


def helper_gen_lendel_msg_field(f_idx: int, f_val: bytes):
    # manual encoding of protobuf data
    f_wt = 2  # field type 2 (length delimited messag)
    tag = (f_idx << 3) | f_wt  # combined tag
    msg = helper_encode_base128le(tag)  # add encoded tag to message
    msg = msg + helper_encode_base128le(len(f_val))  # add length of message
    msg = msg + f_val
    return msg


def helper_gen_bits64_msg_field_packed(f_idx: int, values: list[int]):
    # manual encoding of protobuf data
    msg_inner = b""
    for f_val in values:
        msg_inner = msg_inner + struct.pack("<Q", f_val)  # add bits64 encoded field value
    return helper_gen_lendel_msg_field(f_idx, msg_inner)


def helper_gen_bits32_msg_field_packed(f_idx: int, values: list[int]):
    # manual encoding of protobuf data
    msg_inner = b""
    for f_val in values:
        msg_inner = msg_inner + struct.pack("<I", f_val)  # add bits32 encoded field value
    return helper_gen_lendel_msg_field(f_idx, msg_inner)


def helper_gen_varint_msg_field_packed(f_idx: int, values: list[int]):
    # manual encoding of protobuf data
    msg_inner = b""
    for f_val in values:
        msg_inner = msg_inner + helper_encode_base128le(f_val)  # add varint encoded field value
    return helper_gen_lendel_msg_field(f_idx, msg_inner)


def helper_gen_lendel_msg_field_packed(f_idx: int, values: list[bytes]):
    # manual encoding of protobuf data
    msg_inner = b""
    for f_val in values:
        msg_inner = msg_inner + helper_encode_base128le(len(f_val))  # add length of message
        msg_inner = msg_inner + f_val
    return helper_gen_lendel_msg_field(f_idx, msg_inner)


def test_special_decoding():
    msg = helper_gen_varint_msg_field(1, 1)  # small varint
    msg += helper_gen_varint_msg_field(2, 1 << 32)  # varint > 32bit
    msg += helper_gen_varint_msg_field(3, 1 << 64)  # varint > 64bit (returned as 0x0 by Kaitai protobuf decoder)
    msg += helper_gen_bits32_msg_field(4, 0xbf8ccccd)  # bits32
    msg += helper_gen_bits64_msg_field(5, 0xbff199999999999a)  # bits64
    msg += helper_gen_varint_msg_field(6, 0xffffffff)  # 32 bit varint negative
    msg += helper_gen_lendel_msg_field(7, b"hello world")  # length delimted message, UTF-8 parsable
    msg += helper_gen_varint_msg_field(8, 1 << 128)  # oversized varint

    parser = ProtoParser(
        data=msg,
        parser_options=ProtoParser.ParserOptions(),
        rules=[]
    )

    fields = parser.root_fields
    assert fields[0].wire_value == 1
    assert fields[1].wire_value == 1 << 32
    as_bool = fields[1].decode_as(ProtoParser.DecodedTypes.bool)
    assert isinstance(as_bool, bool)
    assert as_bool
    as_bool = fields[2].decode_as(ProtoParser.DecodedTypes.bool)
    assert isinstance(as_bool, bool)
    assert not as_bool
    assert fields[1].decode_as(ProtoParser.DecodedTypes.float) == 2.121995791e-314
    assert fields[1].safe_decode_as(ProtoParser.DecodedTypes.uint32) == (ProtoParser.DecodedTypes.uint64, 1 << 32)
    assert fields[0].safe_decode_as(ProtoParser.DecodedTypes.sfixed32) == (ProtoParser.DecodedTypes.uint32, 1)
    assert fields[3].wire_type == ProtoParser.WireTypes.bit_32
    assert fields[4].wire_type == ProtoParser.WireTypes.bit_64
    # signed 32 bit int (standard encoding)
    assert fields[5].safe_decode_as(ProtoParser.DecodedTypes.int32) == (ProtoParser.DecodedTypes.int32, -1)
    # fixed (signed) 32bit int (ZigZag encoding)
    assert fields[5].safe_decode_as(ProtoParser.DecodedTypes.sint32) == (ProtoParser.DecodedTypes.sint32, -2147483648)
    # sint64
    assert fields[1].safe_decode_as(ProtoParser.DecodedTypes.sint64) == (ProtoParser.DecodedTypes.sint64, 2147483648)
    # int64
    assert fields[1].safe_decode_as(ProtoParser.DecodedTypes.int64) == (ProtoParser.DecodedTypes.int64, 4294967296)

    # varint 64bit to enum
    assert fields[1].safe_decode_as(ProtoParser.DecodedTypes.enum) == (ProtoParser.DecodedTypes.enum, 4294967296)

    # bits64 to sfixed64
    assert fields[4].safe_decode_as(ProtoParser.DecodedTypes.sfixed64) == (ProtoParser.DecodedTypes.sfixed64, -4615739258092021350)
    # bits64 to fixed64
    assert fields[4].safe_decode_as(ProtoParser.DecodedTypes.fixed64) == (ProtoParser.DecodedTypes.fixed64, 0xbff199999999999a)
    # bits64 to double
    assert fields[4].safe_decode_as(ProtoParser.DecodedTypes.double) == (ProtoParser.DecodedTypes.double, -1.1)
    # bits64 to float --> failover fixed64 (64bit to large for double)
    assert fields[4].safe_decode_as(ProtoParser.DecodedTypes.float) == (ProtoParser.DecodedTypes.fixed64, 0xbff199999999999a)

    # bits32 to sfixed32
    assert fields[3].safe_decode_as(ProtoParser.DecodedTypes.sfixed32) == (ProtoParser.DecodedTypes.sfixed32, -1081291571)
    # bits32 to fixed32
    assert fields[3].safe_decode_as(ProtoParser.DecodedTypes.fixed32) == (ProtoParser.DecodedTypes.fixed32, 0xbf8ccccd)
    # bits32 to float
    assert fields[3].safe_decode_as(ProtoParser.DecodedTypes.float) == (ProtoParser.DecodedTypes.float, -1.100000023841858)
    # bits32 to string --> failover fixed32
    assert fields[3].safe_decode_as(ProtoParser.DecodedTypes.string) == (ProtoParser.DecodedTypes.fixed32, 0xbf8ccccd)

    # length delimeted to string
    assert fields[6].safe_decode_as(ProtoParser.DecodedTypes.string) == (ProtoParser.DecodedTypes.string, "hello world")
    # length delimeted to bytes
    assert fields[6].safe_decode_as(ProtoParser.DecodedTypes.bytes) == (ProtoParser.DecodedTypes.bytes, b"hello world")

    assert fields[0].wire_value_as_utf8() == "1"

    with pytest.raises(TypeError, match="intended decoding mismatches wire type"):
        fields[0].decode_as(ProtoParser.DecodedTypes.sfixed32)
    with pytest.raises(TypeError, match="wire value too large for int32"):
        fields[1].decode_as(ProtoParser.DecodedTypes.int32)
    with pytest.raises(TypeError, match="wire value too large for sint32"):
        fields[1].decode_as(ProtoParser.DecodedTypes.sint32)
    with pytest.raises(TypeError, match="wire value too large for uint32"):
        fields[1].decode_as(ProtoParser.DecodedTypes.uint32)
    with pytest.raises(TypeError, match="can not be converted to floatingpoint representation"):
        fields[6]._wire_value_as_float()
    with pytest.raises(TypeError, match="wire value too large for int64"):
        fields[7].decode_as(ProtoParser.DecodedTypes.int64)
    with pytest.raises(TypeError, match="wire value too large"):
        fields[7].decode_as(ProtoParser.DecodedTypes.uint64)
    with pytest.raises(TypeError, match="wire value too large for sint64"):
        fields[7].decode_as(ProtoParser.DecodedTypes.sint64)
    with pytest.raises(ValueError, match="varint exceeds bounds of provided data"):
        ProtoParser.read_fields(
            wire_data=helper_encode_base128le(1 << 128),
            options=ProtoParser.ParserOptions(),
            parent_field=None,
            rules=[]
        )
    with pytest.raises(ValueError, match="value exceeds 64bit, violating protobuf specs"):
        fields = ProtoParser.read_fields(
            wire_data=helper_gen_varint_msg_field(1, 1 << 128),
            options=ProtoParser.ParserOptions(),
            parent_field=None,
            rules=[]
        )
        fields[0]._value_as_bytes()
    with pytest.raises(ValueError, match=".* is not a valid .*WireTypes"):
        ProtoParser.read_fields(
            wire_data=helper_encode_base128le(0x7),  # invalid wiretype 0x7
            options=ProtoParser.ParserOptions(),
            parent_field=None,
            rules=[]
        )


def test_view_protobuf_custom_config_packed(tdata):
    # message with repeated field fixed64
    msg_inner1 = helper_gen_bits64_msg_field(2, 12)
    msg_inner1 += helper_gen_bits64_msg_field(2, 23)
    msg_inner1 += helper_gen_bits64_msg_field(2, 456789012345678)
    msg1 = helper_gen_lendel_msg_field(1, msg_inner1)

    v = full_eval(ViewGrpcProtobuf())
    view_text, output = v(msg1)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '  '), ('text', '1    '), ('text', '                 ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.2  '), ('text', '12               ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.2  '), ('text', '23               ')],
        [('text', '[fixed64]  '), ('text', '  '), ('text', '1.2  '), ('text', '456789012345678  ')]
    ]

    # same message as above, but fixed64 values are packed
    # Note: the decoded has no type indication, as packed values are always contained in
    #       a length delimited field. The packed fields contain no individual type header

    # decoder has no knowledge of packed repeated field
    msg_inner2 = helper_gen_bits64_msg_field_packed(2, [12, 23, 456789012345678])
    msg2 = helper_gen_lendel_msg_field(1, msg_inner2)
    view_text, output = v(msg2)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '  '), ('text', '1    '), ('text', '                                                                                         ')],  # noqa: E501
        [('text', '[bytes]    '), ('text', '  '), ('text', '1.2  '), ('text', "b'\\x0c\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x17\\x00\\x00\\x00\\x00\\x00\\x00\\x00Ns\\xd1zr\\x9f\\x01\\x00'  ")]  # noqa: E501
    ]

    # decoder uses custom definition to decode as 1.2 as "packed, repeated fixed64"
    view_config = ViewConfig(
        parser_options=ProtoParser.ParserOptions(),
        parser_rules=[
            ProtoParser.ParserRule(
                filter=".*",
                name="parse packed field",
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(
                        name="packed repeated fixed64",
                        tag="1.2",
                        intended_decoding=ProtoParser.DecodedTypes.fixed64,
                        as_packed=True
                    )
                ]
            )
        ]
    )
    v = full_eval(ViewGrpcProtobuf(view_config))
    msg_inner2 = helper_gen_bits64_msg_field_packed(2, [12, 23, 456789012345678])
    msg2 = helper_gen_lendel_msg_field(1, msg_inner2)
    # provide the view a flow and response message dummies, to allow custom rules to work
    view_text, output = v(msg2, flow=sim_flow, http_message=sim_flow.response)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '                         '), ('text', '1    '), ('text', '                 ')],
        [('text', '[fixed64]  '), ('text', 'packed repeated fixed64  '), ('text', '1.2  '), ('text', '12               ')],
        [('text', '[fixed64]  '), ('text', 'packed repeated fixed64  '), ('text', '1.2  '), ('text', '23               ')],
        [('text', '[fixed64]  '), ('text', 'packed repeated fixed64  '), ('text', '1.2  '), ('text', '456789012345678  ')]
    ]

    # message with packed repeated messages in field 1.5
    # Note: protobuf v3 only allows packed encoding for scalar field types, but packed messages
    #       were spotted in traffic to google gRPC endpoints (f.e. https://play.googleapis.com/log/batch)
    p_msg1 = helper_gen_lendel_msg_field(1, b"inner message 1")
    p_msg1 += helper_gen_varint_msg_field(2, 1)
    p_msg2 = helper_gen_lendel_msg_field(1, b"inner message 2")
    p_msg2 += helper_gen_varint_msg_field(2, 2)
    p_msg3 = helper_gen_lendel_msg_field(1, b"inner message 3")
    p_msg3 += helper_gen_varint_msg_field(2, 3)
    msg_inner3 = helper_gen_lendel_msg_field_packed(5, [p_msg1, p_msg2, p_msg3])
    msg3 = helper_gen_lendel_msg_field(1, msg_inner3)
    view_config = ViewConfig(
        parser_options=ProtoParser.ParserOptions(),
        parser_rules=[
            ProtoParser.ParserRule(
                filter=".*",
                name="parse packed field",
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(
                        name="packed repeated message",
                        tag="1.5",
                        intended_decoding=ProtoParser.DecodedTypes.message,
                        as_packed=True
                    )
                ]
            )
        ]
    )
    v = full_eval(ViewGrpcProtobuf(view_config))
    # provide the view a flow and response message dummies, to allow custom rules to work
    view_text, output = v(msg3, flow=sim_flow, http_message=sim_flow.response)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '                         '), ('text', '1      '), ('text', '                 ')],
        [('text', '[message]  '), ('text', 'packed repeated message  '), ('text', '1.5    '), ('text', '                 ')],
        [('text', '[string]   '), ('text', '                         '), ('text', '1.5.1  '), ('text', 'inner message 1  ')],
        [('text', '[uint32]   '), ('text', '                         '), ('text', '1.5.2  '), ('text', '1                ')],
        [('text', '[message]  '), ('text', 'packed repeated message  '), ('text', '1.5    '), ('text', '                 ')],
        [('text', '[string]   '), ('text', '                         '), ('text', '1.5.1  '), ('text', 'inner message 2  ')],
        [('text', '[uint32]   '), ('text', '                         '), ('text', '1.5.2  '), ('text', '2                ')],
        [('text', '[message]  '), ('text', 'packed repeated message  '), ('text', '1.5    '), ('text', '                 ')],
        [('text', '[string]   '), ('text', '                         '), ('text', '1.5.1  '), ('text', 'inner message 3  ')],
        [('text', '[uint32]   '), ('text', '                         '), ('text', '1.5.2  '), ('text', '3                ')]
    ]

    # message with repeated messages in field 1.5 (not packed), has to be detected by failover parsing
    msg_inner4 = helper_gen_lendel_msg_field(5, p_msg1)
    msg_inner4 += helper_gen_lendel_msg_field(5, p_msg2)
    msg_inner4 += helper_gen_lendel_msg_field(5, p_msg3)
    msg4 = helper_gen_lendel_msg_field(1, msg_inner4)
    view_config = ViewConfig(
        parser_options=ProtoParser.ParserOptions(),
        parser_rules=[
            ProtoParser.ParserRule(
                filter=".*",
                name="parse packed field",
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(
                        name="packed repeated message",
                        tag="1.5",
                        intended_decoding=ProtoParser.DecodedTypes.message,
                        as_packed=True
                    )
                ]
            )
        ]
    )
    v = full_eval(ViewGrpcProtobuf(view_config))
    # provide the view a flow and response message dummies, to allow custom rules to work
    view_text, output = v(msg4, flow=sim_flow, http_message=sim_flow.response)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '                         '), ('text', '1      '), ('text', '                 ')],
        [('text', '[message]  '), ('text', 'packed repeated message  '), ('text', '1.5    '), ('text', '                 ')],
        [('text', '[string]   '), ('text', '                         '), ('text', '1.5.1  '), ('text', 'inner message 1  ')],
        [('text', '[uint32]   '), ('text', '                         '), ('text', '1.5.2  '), ('text', '1                ')],
        [('text', '[message]  '), ('text', 'packed repeated message  '), ('text', '1.5    '), ('text', '                 ')],
        [('text', '[string]   '), ('text', '                         '), ('text', '1.5.1  '), ('text', 'inner message 2  ')],
        [('text', '[uint32]   '), ('text', '                         '), ('text', '1.5.2  '), ('text', '2                ')],
        [('text', '[message]  '), ('text', 'packed repeated message  '), ('text', '1.5    '), ('text', '                 ')],
        [('text', '[string]   '), ('text', '                         '), ('text', '1.5.1  '), ('text', 'inner message 3  ')],
        [('text', '[uint32]   '), ('text', '                         '), ('text', '1.5.2  '), ('text', '3                ')]
    ]

    # packed bit32
    msg_inner = helper_gen_bits32_msg_field_packed(2, [12, 23, 4567890])
    msg = helper_gen_lendel_msg_field(1, msg_inner)
    view_config = ViewConfig(
        parser_options=ProtoParser.ParserOptions(),
        parser_rules=[
            ProtoParser.ParserRule(
                filter=".*",
                name="parse packed field",
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(
                        name="packed repeated fixed32",
                        tag="1.2",
                        intended_decoding=ProtoParser.DecodedTypes.fixed32,
                        as_packed=True
                    )
                ]
            )
        ]
    )
    v = full_eval(ViewGrpcProtobuf(view_config))
    # provide the view a flow and response message dummies, to allow custom rules to work
    view_text, output = v(msg, flow=sim_flow, http_message=sim_flow.response)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '                         '), ('text', '1    '), ('text', '         ')],
        [('text', '[fixed32]  '), ('text', 'packed repeated fixed32  '), ('text', '1.2  '), ('text', '12       ')],
        [('text', '[fixed32]  '), ('text', 'packed repeated fixed32  '), ('text', '1.2  '), ('text', '23       ')],
        [('text', '[fixed32]  '), ('text', 'packed repeated fixed32  '), ('text', '1.2  '), ('text', '4567890  ')]
    ]

    # packed bit32, invalid
    msg_inner = helper_gen_bits32_msg_field_packed(2, [12, 23, 4567890]) + b"\x01"  # data not divisible by 4
    msg = helper_gen_lendel_msg_field(1, msg_inner)
    view_config = ViewConfig(
        parser_options=ProtoParser.ParserOptions(),
        parser_rules=[
            ProtoParser.ParserRule(
                filter=".*",
                name="parse packed field",
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(
                        name="packed repeated fixed32",
                        tag="1.2",
                        intended_decoding=ProtoParser.DecodedTypes.fixed32,
                        as_packed=True
                    )
                ]
            )
        ]
    )
    v = full_eval(ViewGrpcProtobuf(view_config))
    # provide the view a flow and response message dummies, to allow custom rules to work
    view_text, output = v(msg, flow=sim_flow, http_message=sim_flow.response)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[bytes]  '), ('text', '  '), ('text', '1  '), ('text', "b'\\x12\\x0c\\x0c\\x00\\x00\\x00\\x17\\x00\\x00\\x00R\\xb3E\\x00\\x01'  ")]  # noqa: E501
    ]

    # packed bit64, invalid
    msg_inner = helper_gen_bits64_msg_field_packed(2, [12, 23, 4567890]) + b"\x01"  # data not divisible by 8
    msg = helper_gen_lendel_msg_field(1, msg_inner)
    view_config = ViewConfig(
        parser_options=ProtoParser.ParserOptions(),
        parser_rules=[
            ProtoParser.ParserRule(
                filter=".*",
                name="parse packed field",
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(
                        name="packed repeated fixed64",
                        tag="1.2",
                        intended_decoding=ProtoParser.DecodedTypes.fixed64,
                        as_packed=True
                    )
                ]
            )
        ]
    )
    v = full_eval(ViewGrpcProtobuf(view_config))
    # provide the view a flow and response message dummies, to allow custom rules to work
    view_text, output = v(msg, flow=sim_flow, http_message=sim_flow.response)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[bytes]  '), ('text', '  '), ('text', '1  '), ('text', "b'\\x12\\x18\\x0c\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x17\\x00\\x00\\x00\\x00\\x00\\x00\\x00R\\xb3E\\x00\\x00\\x00\\x00\\x00\\x01'")]  # noqa: E501
    ]

    # packed varint
    msg_inner = helper_gen_varint_msg_field_packed(2, [12, 23, 4567890])
    msg = helper_gen_lendel_msg_field(1, msg_inner)
    view_config = ViewConfig(
        parser_options=ProtoParser.ParserOptions(),
        parser_rules=[
            ProtoParser.ParserRule(
                filter=".*",
                name="parse packed field",
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(
                        name="packed repeated varint",
                        tag="1.2",
                        intended_decoding=ProtoParser.DecodedTypes.uint32,
                        as_packed=True
                    )
                ]
            )
        ]
    )
    v = full_eval(ViewGrpcProtobuf(view_config))
    # provide the view a flow and response message dummies, to allow custom rules to work
    view_text, output = v(msg, flow=sim_flow, http_message=sim_flow.response)
    assert view_text == "Protobuf (flattened)"
    output = list(output)  # assure list conversion if generator
    assert output == [
        [('text', '[message]  '), ('text', '                        '), ('text', '1    '), ('text', '         ')],
        [('text', '[uint32]   '), ('text', 'packed repeated varint  '), ('text', '1.2  '), ('text', '12       ')],
        [('text', '[uint32]   '), ('text', 'packed repeated varint  '), ('text', '1.2  '), ('text', '23       ')],
        [('text', '[uint32]   '), ('text', 'packed repeated varint  '), ('text', '1.2  '), ('text', '4567890  ')]
    ]


def test_render_priority():
    v = grpc.ViewGrpcProtobuf()
    assert v.render_priority(b"data", content_type="application/x-protobuf")
    assert v.render_priority(b"data", content_type="application/x-protobuffer")
    assert v.render_priority(b"data", content_type="application/grpc-proto")
    assert v.render_priority(b"data", content_type="application/grpc")
    assert v.render_priority(b"data", content_type="application/prpc")
    assert not v.render_priority(b"data", content_type="text/plain")
