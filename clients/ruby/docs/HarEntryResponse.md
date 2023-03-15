# BrowserupMitmProxy::HarEntryResponse

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **status** | **Integer** |  |  |
| **status_text** | **String** |  |  |
| **http_version** | **String** |  |  |
| **cookies** | [**Array&lt;HarEntryRequestCookiesInner&gt;**](HarEntryRequestCookiesInner.md) |  |  |
| **headers** | [**Array&lt;Header&gt;**](Header.md) |  |  |
| **content** | [**HarEntryResponseContent**](HarEntryResponseContent.md) |  |  |
| **redirect_url** | **String** |  |  |
| **headers_size** | **Integer** |  |  |
| **body_size** | **Integer** |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::HarEntryResponse.new(
  status: null,
  status_text: null,
  http_version: null,
  cookies: null,
  headers: null,
  content: null,
  redirect_url: null,
  headers_size: null,
  body_size: null,
  comment: null
)
```

