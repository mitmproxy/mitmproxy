# BrowserupMitmProxy::EntryRequest

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **method** | **String** |  |  |
| **url** | **String** |  |  |
| **http_version** | **String** |  |  |
| **cookies** | [**Array&lt;EntryRequestCookiesInner&gt;**](EntryRequestCookiesInner.md) |  |  |
| **headers** | [**Array&lt;Header&gt;**](Header.md) |  |  |
| **query_string** | [**Array&lt;EntryRequestQueryStringInner&gt;**](EntryRequestQueryStringInner.md) |  |  |
| **post_data** | [**EntryRequestPostData**](EntryRequestPostData.md) |  | [optional] |
| **headers_size** | **Integer** |  |  |
| **body_size** | **Integer** |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::EntryRequest.new(
  method: null,
  url: null,
  http_version: null,
  cookies: null,
  headers: null,
  query_string: null,
  post_data: null,
  headers_size: null,
  body_size: null,
  comment: null
)
```

