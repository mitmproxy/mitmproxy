# BrowserupMitmProxy::MatchCriteria

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **url** | **String** | Request URL regexp to match | [optional] |
| **page** | **String** | current|all | [optional] |
| **status** | **String** | HTTP Status code to match. | [optional] |
| **content** | **String** | Body content regexp content to match | [optional] |
| **content_type** | **String** | Content type | [optional] |
| **websocket_message** | **String** | Websocket message text to match | [optional] |
| **request_header** | [**NameValuePair**](NameValuePair.md) |  | [optional] |
| **request_cookie** | [**NameValuePair**](NameValuePair.md) |  | [optional] |
| **response_header** | [**NameValuePair**](NameValuePair.md) |  | [optional] |
| **response_cookie** | [**NameValuePair**](NameValuePair.md) |  | [optional] |
| **json_valid** | **Boolean** | Is valid JSON | [optional] |
| **json_path** | **String** | Has JSON path | [optional] |
| **json_schema** | **String** | Validates against passed JSON schema | [optional] |
| **error_if_no_traffic** | **Boolean** | If the proxy has NO traffic at all, return error | [optional][default to true] |

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

