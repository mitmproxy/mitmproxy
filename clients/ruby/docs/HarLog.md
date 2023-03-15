# BrowserupMitmProxy::HarLog

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **version** | **String** |  |  |
| **creator** | [**HarLogCreator**](HarLogCreator.md) |  |  |
| **browser** | [**HarLogCreator**](HarLogCreator.md) |  | [optional] |
| **pages** | [**Array&lt;Page&gt;**](Page.md) |  |  |
| **entries** | [**Array&lt;HarEntry&gt;**](HarEntry.md) |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::HarLog.new(
  version: null,
  creator: null,
  browser: null,
  pages: null,
  entries: null,
  comment: null
)
```

