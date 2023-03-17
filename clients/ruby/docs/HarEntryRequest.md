# BrowserupMitmProxy::HarEntryRequest

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **method** | **String** |  |  |
| **url** | **String** |  |  |
| **http_version** | **String** |  |  |
| **cookies** | [**Array&lt;HarEntryRequestCookiesInner&gt;**](HarEntryRequestCookiesInner.md) |  |  |
| **headers** | [**Array&lt;Header&gt;**](Header.md) |  |  |
| **query_string** | [**Array&lt;HarEntryRequestQueryStringInner&gt;**](HarEntryRequestQueryStringInner.md) |  |  |
| **post_data** | [**HarEntryRequestPostData**](HarEntryRequestPostData.md) |  | [optional] |
| **headers_size** | **Integer** |  |  |
| **body_size** | **Integer** |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::HarEntryRequest.new(
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

