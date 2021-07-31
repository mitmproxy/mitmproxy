# BrowserupProxy::EntryTimings

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **dns** | **Float** |  | [optional] |
| **connect** | **Float** |  | [optional] |
| **blocked** | **Float** |  | [optional] |
| **_send** | **Float** |  |  |
| **wait** | **Float** |  |  |
| **receive** | **Float** |  |  |
| **ssl** | **Float** |  | [optional] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::EntryTimings.new(
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

