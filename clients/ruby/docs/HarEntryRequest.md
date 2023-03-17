# BrowserupMitmProxy::HarEntryRequest

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **method** | **Object** |  |  |
| **url** | **Object** |  |  |
| **http_version** | **Object** |  |  |
| **cookies** | **Object** |  |  |
| **headers** | **Object** |  |  |
| **query_string** | **Object** |  |  |
| **post_data** | [**HarEntryRequestPostData**](HarEntryRequestPostData.md) |  | [optional] |
| **headers_size** | **Object** |  |  |
| **body_size** | **Object** |  |  |
| **comment** | **Object** |  | [optional] |

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

