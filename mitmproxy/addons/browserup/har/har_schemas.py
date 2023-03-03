from marshmallow import Schema, fields


class VerifyResultSchema(Schema):
    result = fields.Boolean(required=True, description="Result True / False")
    name = fields.Str(required=True, description="Name")
    type = fields.Str(required=True, description="Type")


class NameValuePairSchema(Schema):
    name = fields.Str(optional=True, description="Name to match")
    value = fields.Str(optional=True, description="Value to match")


class ErrorSchema(Schema):
    name = fields.Str(optional=False, description="Name of the Error to add. Stored in har under _errors")
    details = fields.Str(optional=False, description="Short details of the error")


class CounterSchema(Schema):
    name = fields.Str(required=True, description="Name of Custom Counter value you are adding to the page under _counters")
    value = fields.Number(required=True, format="double", description="Value for the counter")

class PageTimingSchema(Schema):
    onContentLoad = fields.Number(required=True, description="onContentLoad per the browser")
    onLoad = fields.Number(required=True, description="onLoad per the browser")
    name = fields.Str(required=False, description="Name of Custom Counter value you are adding to the page under counters")
    value = fields.Number(required=False, format="double", description="Value for the counter")
    _firstInputDelay = fields.Number(required=False, description="firstInputDelay from the browser")
    _firstPaint = fields.Number(required=False, description="firstPaint from the browser")
    _cumulativeLayoutShift = fields.Number(required=False, description="cumulativeLayoutShift metric from the browser")
    _largestContentFullPaint = fields.Number(required=False, description="largestContentFullPaint from the browser")
    _domInteractive = fields.Number(required=False, description="domInteractive from the browser")
    _firstContentfulPaint = fields.Number(required=False, description="firstContentfulPaint from the browser")
    _dns = fields.Number(required=False, description="dns lookup time from the browser")
    _ssl = fields.Number(required=False, description="Ssl connect time from the browser")
    _ttfb = fields.Number(required=False, description="Time to first byte of the page's first request per the browser")
    _href =  fields.Str(required=False, description="Top level href, including hashtag, etc per the browser")


class MatchCriteriaSchema(Schema):
    url = fields.Str(optional=True, description="Request URL regexp to match", externalDocs={
                     'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    page = fields.Str(optional=True, description="current|all", externalDocs={
                      'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    status = fields.Str(optional=True, description="HTTP Status code to match.", externalDocs={
                        'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    content = fields.Str(optional=True, description="Body content regexp content to match", externalDocs={
                         'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    content_type = fields.Str(optional=True, description="Content type", externalDocs={
                              'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    websocket_message = fields.Str(optional=True, description="Websocket message text to match", externalDocs={
                                   'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    request_header = fields.Nested(NameValuePairSchema, optional=True, externalDocs={
                                   'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    request_cookie = fields.Nested(NameValuePairSchema, optional=True, externalDocs={
                                   'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    response_header = fields.Nested(NameValuePairSchema, optional=True, externalDocs={
                                    'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    response_cookie = fields.Nested(NameValuePairSchema, optional=True, externalDocs={
                                    'description': 'Python Regex', 'url': 'https://docs.python.org/3/howto/regex.html'})
    json_valid = fields.Boolean(optional=True, description="Is valid JSON")
    json_path = fields.Str(optional=True, description="Has JSON path")
    json_schema = fields.Str(optional=True, description="Validates against passed JSON schema")
    error_if_no_traffic = fields.Boolean(optional=True, default=True, description="If the proxy has NO traffic at all, return error")

    class Meta:
        ordered = True
        description = """A set of criteria for filtering HTTP Requests and Responses.
                         Criteria are AND based, and use python regular expressions for string comparison"""
        externalDocs = {'description': 'Python Regex Doc', 'url': 'https://docs.python.org/3/howto/regex.html'}
