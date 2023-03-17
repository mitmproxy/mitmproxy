# BrowserupMitmProxy::HarEntryTimings

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **dns** | **Object** |  |  |
| **connect** | **Object** |  |  |
| **blocked** | **Object** |  |  |
| **_send** | **Object** |  |  |
| **wait** | **Object** |  |  |
| **receive** | **Object** |  |  |
| **ssl** | **Object** |  |  |
| **comment** | **Object** |  | [optional] |

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

