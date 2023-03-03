# BrowserupMitmProxy::HarEntryCache

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **before_request** | [**HarEntryCacheBeforeRequest**](HarEntryCacheBeforeRequest.md) |  | [optional] |
| **after_request** | [**HarEntryCacheBeforeRequest**](HarEntryCacheBeforeRequest.md) |  | [optional] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::HarEntryCache.new(
  before_request: null,
  after_request: null,
  comment: null
)
```

