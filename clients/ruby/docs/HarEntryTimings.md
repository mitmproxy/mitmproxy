# BrowserupMitmProxy::HarEntryTimings

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **dns** | **Integer** |  | [default to -1] |
| **connect** | **Integer** |  | [default to -1] |
| **blocked** | **Integer** |  | [default to -1] |
| **_send** | **Integer** |  | [default to -1] |
| **wait** | **Integer** |  | [default to -1] |
| **receive** | **Integer** |  | [default to -1] |
| **ssl** | **Integer** |  | [default to -1] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::HarEntryTimings.new(
  dns: null,
  connect: null,
  blocked: null,
  _send: null,
  wait: null,
  receive: null,
  ssl: null,
  comment: null
)
```

