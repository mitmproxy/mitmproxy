import marshmallow
from marshmallow import Schema, fields


class MatchCriteriaSchema(Schema):
    status_code = fields.Str(optional=True,  description="Status code to match. Strings of format 2xx or 4xx indicate anything in range")
    url = fields.Str(optional=True, description="Request URL regexp to match")
    content = fields.Str(optional=True, description="Body URL regexp content to match")
    request_header = fields.Str(optional=True, description="Header URL regexp text to match")
    response_header = fields.Str(optional=True, description="Response Header text to match")
    websocket_message = fields.Str(optional=True, description="Websocket message text to match")
    step = fields.Str(optional=True, description="current|all")
    content_type = fields.Str(optional=True, description="Websocket message text to match")

class PageCriteriaSchema(Schema):
    onload = fields.Int(optional=True, description="Maximum milliseconds to pass")
    first_contentful_paint = fields.Int(optional=True, description="Maximum milliseconds to pass")
    oncontentload = fields.Int(optional=True, description="Maximum milliseconds to pass")


class UrlCriteriaSchema(Schema):
    time = fields.Int(optional=True, description="Maximum milliseconds to pass")

class AssetCriteriaSchema(Schema):
    max_size = fields.Int(optional=True, description="Maximum size")
    total_size  = fields.Int(optional=True, description="Total size size")

class HarPageSchema(Schema):
    title = fields.Str(required=True,  description="Page title")
    page_id = fields.Str(optional=True, description="Internal unique ID for har - auto-populated")

class CustomHarDataSchema(Schema):
    page = fields.Dict(required=True,  description="Counters for the page section of the current page")