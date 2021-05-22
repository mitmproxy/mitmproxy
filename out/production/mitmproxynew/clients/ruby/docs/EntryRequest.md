# BrowserupProxy::EntryRequest

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **method** | **String** |  |  |
| **url** | **String** |  |  |
| **http_version** | **String** |  |  |
| **cookies** | [**Array&lt;EntryRequestCookies&gt;**](EntryRequestCookies.md) |  |  |
| **headers** | [**Array&lt;Header&gt;**](Header.md) |  |  |
| **query_string** | [**Array&lt;EntryRequestQueryString&gt;**](EntryRequestQueryString.md) |  |  |
| **post_data** | **Object** | Posted data info. | [optional] |
| **headers_size** | **Integer** |  |  |
| **body_size** | **Integer** |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::EntryRequest.new(
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

