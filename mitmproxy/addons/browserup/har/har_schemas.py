from marshmallow import fields
from marshmallow import Schema


class VerifyResultSchema(Schema):
    result = fields.Boolean(
        metadata={"optional": False, "description": "Result True / False"}
    )
    name = fields.Str(metadata={"optional": False, "description": "Name"})
    type = fields.Str(metadata={"optional": False, "description": "Type"})


class NameValuePairSchema(Schema):
    name = fields.Str(metadata={"optional": True, "description": "Name to match"})
    value = fields.Str(metadata={"optional": True, "description": "Value to match"})


class ErrorSchema(Schema):
    name = fields.Str(
        metadata={
            "optional": False,
            "description": "Name of the Error to add. Stored in har under _errors",
        }
    )
    details = fields.Str(
        metadata={"optional": False, "description": "Short details of the error"}
    )


class MetricSchema(Schema):
    name = fields.Str(
        metadata={
            "optional": False,
            "description": "Name of Custom Metric to add to the page under _metrics",
        }
    )
    value = fields.Number(
        metadata={
            "optional": False,
            "format": "double",
            "description": "Value for the metric",
        }
    )


class PageTimingSchema(Schema):
    onContentLoad = fields.Number(
        metadata={"optional": False, "description": "onContentLoad per the browser"}
    )
    onLoad = fields.Number(
        metadata={"optional": False, "description": "onLoad per the browser"}
    )
    _firstInputDelay = fields.Number(
        metadata={"optional": True, "description": "firstInputDelay from the browser"}
    )
    _firstPaint = fields.Number(
        metadata={"optional": True, "description": "firstPaint from the browser"}
    )
    _cumulativeLayoutShift = fields.Number(
        metadata={
            "optional": True,
            "description": "cumulativeLayoutShift metric from the browser",
        }
    )
    _largestContentfulPaint = fields.Number(
        metadata={
            "optional": True,
            "description": "largestContentfulPaint from the browser",
        }
    )
    _domInteractive = fields.Number(
        metadata={"optional": True, "description": "domInteractive from the browser"}
    )
    _firstContentfulPaint = fields.Number(
        metadata={
            "optional": True,
            "description": "firstContentfulPaint from the browser",
        }
    )
    _dns = fields.Number(
        metadata={"optional": True, "description": "dns lookup time from the browser"}
    )
    _ssl = fields.Number(
        metadata={"optional": True, "description": "Ssl connect time from the browser"}
    )
    _timeToFirstByte = fields.Number(
        metadata={
            "optional": True,
            "description": "Time to first byte of the page's first request per the browser",
        }
    )
    _href = fields.Str(
        metadata={
            "optional": True,
            "description": "Top level href, including hashtag, etc per the browser",
        }
    )


class MatchCriteriaSchema(Schema):
    url = fields.Str(
        metadata={
            "optional": True,
            "description": "Request URL regexp to match",
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        }
    )
    page = fields.Str(
        metadata={
            "optional": True,
            "description": "current|all",
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        }
    )
    status = fields.Str(
        metadata={
            "optional": True,
            "description": "HTTP Status code to match.",
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        }
    )
    content = fields.Str(
        metadata={
            "optional": True,
            "description": "Body content regexp content to match",
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        }
    )
    content_type = fields.Str(
        metadata={
            "optional": True,
            "description": "Content type",
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        }
    )
    websocket_message = fields.Str(
        metadata={
            "optional": True,
            "description": "Websocket message text to match",
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        }
    )
    request_header = fields.Nested(
        NameValuePairSchema,
        metadata={
            "optional": True,
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        },
    )
    request_cookie = fields.Nested(
        NameValuePairSchema,
        metadata={
            "optional": True,
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        },
    )
    response_header = fields.Nested(
        NameValuePairSchema,
        metadata={
            "optional": True,
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        },
    )
    response_cookie = fields.Nested(
        NameValuePairSchema,
        metadata={
            "optional": True,
            "externalDocs": {
                "description": "Python Regex",
                "url": "https://docs.python.org/3/howto/regex.html",
            },
        },
    )
    json_valid = fields.Boolean(
        metadata={"optional": True, "description": "Is valid JSON"}
    )
    json_path = fields.Str(metadata={"optional": True, "description": "Has JSON path"})
    json_schema = fields.Str(
        metadata={
            "optional": True,
            "description": "Validates against passed JSON schema",
        }
    )
    error_if_no_traffic = fields.Boolean(
        metadata={
            "optional": True,
            "default": True,
            "description": "If the proxy has NO traffic at all, return error",
        }
    )

    class Meta:
        ordered = True
        description = """A set of criteria for filtering HTTP Requests and Responses.
                         Criteria are AND based, and use python regular expressions for string comparison"""
        externalDocs = {
            "description": "Python Regex Doc",
            "url": "https://docs.python.org/3/howto/regex.html",
        }
