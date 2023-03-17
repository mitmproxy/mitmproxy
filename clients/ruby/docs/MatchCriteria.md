# BrowserupMitmProxy::MatchCriteria

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **url** | **Object** | Request URL regexp to match | [optional] |
| **page** | **Object** | current|all | [optional] |
| **status** | **Object** | HTTP Status code to match. | [optional] |
| **content** | **Object** | Body content regexp content to match | [optional] |
| **content_type** | **Object** | Content type | [optional] |
| **websocket_message** | **Object** | Websocket message text to match | [optional] |
| **request_header** | **Object** |  | [optional] |
| **request_cookie** | **Object** |  | [optional] |
| **response_header** | **Object** |  | [optional] |
| **response_cookie** | **Object** |  | [optional] |
| **json_valid** | **Object** | Is valid JSON | [optional] |
| **json_path** | **Object** | Has JSON path | [optional] |
| **json_schema** | **Object** | Validates against passed JSON schema | [optional] |
| **error_if_no_traffic** | **Object** | If the proxy has NO traffic at all, return error | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::MatchCriteria.new(
  url: null,
  page: null,
  status: null,
  content: null,
  content_type: null,
  websocket_message: null,
  request_header: null,
  request_cookie: null,
  response_header: null,
  response_cookie: null,
  json_valid: null,
  json_path: null,
  json_schema: null,
  error_if_no_traffic: null
)
```

