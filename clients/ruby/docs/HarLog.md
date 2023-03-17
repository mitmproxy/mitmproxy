# BrowserupMitmProxy::HarLog

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **version** | **Object** |  |  |
| **creator** | [**HarLogCreator**](HarLogCreator.md) |  |  |
| **browser** | [**HarLogCreator**](HarLogCreator.md) |  | [optional] |
| **pages** | **Object** |  |  |
| **entries** | **Object** |  |  |
| **comment** | **Object** |  | [optional] |

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

