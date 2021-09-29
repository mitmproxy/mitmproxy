# BrowserupProxy::PagePageTimings

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **on_content_load** | **Integer** |  | [default to -1] |
| **on_load** | **Integer** |  | [default to -1] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::PagePageTimings.new(
  on_content_load: null,
  on_load: null,
  comment: null
)
```

