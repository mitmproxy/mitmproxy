# BrowserupMitmProxy::HarEntryResponse

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **status** | **Object** |  |  |
| **status_text** | **Object** |  |  |
| **http_version** | **Object** |  |  |
| **cookies** | **Object** |  |  |
| **headers** | **Object** |  |  |
| **content** | [**HarEntryResponseContent**](HarEntryResponseContent.md) |  |  |
| **redirect_url** | **Object** |  |  |
| **headers_size** | **Object** |  |  |
| **body_size** | **Object** |  |  |
| **comment** | **Object** |  | [optional] |

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

