"""
Add a custom version of the gRPC/protobuf content view, which parses
protobuf messages based on a user defined rule set.

"""
from mitmproxy import contentviews
from mitmproxy.contentviews.grpc import ViewGrpcProtobuf, ViewConfig, ProtoParser

config: ViewConfig = ViewConfig()
config.parser_rules = [
    # Note:
    #
    # The first two ParserRules use the same flow filter, although one should reply to request messages and the other to responses.
    # Even with '~s' and '~q' filter expressions, the whole flow would be matched (for '~s') or not matched at all (for '~q'), if
    # the contentview displays a http.Message belonging to a flow with existing request and response.
    # The rules would have to be applied on per-message-basis, instead of per-flow-basis to distinguish request and response (the
    # contentview deals with a single message, either request or response, the flow filter with a flow contiaing both).
    #
    # Thus different ParserRule classes are used to restrict rules to requests or responses were needed:
    #
    # - ParserRule: applied to requests and responses
    # - ParserRuleRequest: applies to requests only
    # - ParserRuleResponse: applies to responses only
    #
    # The actual 'filter' definition in the rule, would still match the whole flow. This means '~u' expressions could
    # be used, to match the URL from the request of a flow, while the ParserRuleResponse is only applied to the response.

    ProtoParser.ParserRuleRequest(
        name = "Google reverse Geo coordinate lookup request",
        filter = "geomobileservices-pa.googleapis.com/google.internal.maps.geomobileservices.geocoding.v3mobile.GeocodingService/ReverseGeocode",  # noqa: E501
        field_definitions=[
            ProtoParser.ParserFieldDefinition(tag="1", name="position"),
            ProtoParser.ParserFieldDefinition(tag="1.1", name="latitude", intended_decoding=ProtoParser.DecodedTypes.double),
            ProtoParser.ParserFieldDefinition(tag="1.2", name="longitude", intended_decoding=ProtoParser.DecodedTypes.double),
            ProtoParser.ParserFieldDefinition(tag="3", name="country"),
            ProtoParser.ParserFieldDefinition(tag="7", name="app"),
        ]
    ),
    ProtoParser.ParserRuleResponse(
        name = "Google reverse Geo coordinate lookup response",
        filter = "geomobileservices-pa.googleapis.com/google.internal.maps.geomobileservices.geocoding.v3mobile.GeocodingService/ReverseGeocode",  # noqa: E501
        field_definitions=[
            ProtoParser.ParserFieldDefinition(tag="1.2", name="address"),
            ProtoParser.ParserFieldDefinition(tag="1.3", name="address array element"),
            ProtoParser.ParserFieldDefinition(tag="1.3.2", name="element value long"),
            ProtoParser.ParserFieldDefinition(tag="1.3.3", name="element value short"),
            ProtoParser.ParserFieldDefinition(tag="", tag_prefixes=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="position"),
            ProtoParser.ParserFieldDefinition(tag=".1", tag_prefixes=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="latitude", intended_decoding=ProtoParser.DecodedTypes.double),  # noqa: E501
            ProtoParser.ParserFieldDefinition(tag=".2", tag_prefixes=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="longitude", intended_decoding=ProtoParser.DecodedTypes.double),  # noqa: E501
            ProtoParser.ParserFieldDefinition(tag="7", name="app"),
        ]
    ),
    ProtoParser.ParserRuleRequest(
        name = "Snapchat targeting query request",
        filter = "api.snapchat.com/snapchat.cdp.cof.CircumstancesService/targetingQuery",
        field_definitions=[
            ProtoParser.ParserFieldDefinition(tag="", tag_prefixes=["5", "8"], name="res_x"),
            ProtoParser.ParserFieldDefinition(tag="", tag_prefixes=["6", "9"], name="res_y"),
            ProtoParser.ParserFieldDefinition(tag="16", name="guid"),
            ProtoParser.ParserFieldDefinition(tag="24", name="source lib"),
            ProtoParser.ParserFieldDefinition(tag="29", name="timestamp"),
        ]
    ),
]


class ViewGrpcWithRules(ViewGrpcProtobuf):
    name = "customized gRPC/protobuf"

    def __init__(self) -> None:
        super().__init__(config=config)

    def __call__(self, *args, **kwargs) -> contentviews.TViewResult:
        heading, lines = super().__call__(*args, **kwargs)
        return heading + " (addon with custom rules)", lines

    def render_priority(self, *args, **kwargs) -> float:
        # increase priority above default gRPC view
        return super().render_priority(*args, **kwargs) + 1


view = ViewGrpcWithRules()


def load(l):
    contentviews.add(view)


def done():
    contentviews.remove(view)
