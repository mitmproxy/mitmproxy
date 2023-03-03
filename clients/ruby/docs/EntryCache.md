# BrowserupMitmProxy::EntryCache

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **before_request** | [**EntryCacheBeforeRequest**](EntryCacheBeforeRequest.md) |  | [optional] |
| **after_request** | [**EntryCacheBeforeRequest**](EntryCacheBeforeRequest.md) |  | [optional] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::EntryCache.new(
  before_request: null,
  after_request: null,
  comment: null
)
```

