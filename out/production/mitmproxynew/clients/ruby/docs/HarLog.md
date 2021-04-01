# BrowserupProxy::HarLog

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **version** | **String** |  |  |
| **creator** | [**HarLogCreator**](HarLogCreator.md) |  |  |
| **browser** | [**HarLogCreator**](HarLogCreator.md) |  | [optional] |
| **pages** | [**Array&lt;Page&gt;**](Page.md) |  | [optional] |
| **entries** | [**Array&lt;Entry&gt;**](Entry.md) |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::HarLog.new(
  version: null,
  creator: null,
  browser: null,
  pages: null,
  entries: null,
  comment: null
)
```

