# BrowserupMitmProxy::HarEntry

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **pageref** | **String** |  | [optional] |
| **started_date_time** | **Time** |  |  |
| **time** | **Integer** |  |  |
| **request** | [**HarEntryRequest**](HarEntryRequest.md) |  |  |
| **response** | [**HarEntryResponse**](HarEntryResponse.md) |  |  |
| **cache** | [**HarEntryCache**](HarEntryCache.md) |  |  |
| **timings** | [**HarEntryTimings**](HarEntryTimings.md) |  |  |
| **server_ip_address** | **String** |  | [optional] |
| **_web_socket_messages** | [**Array&lt;WebSocketMessage&gt;**](WebSocketMessage.md) |  | [optional] |
| **connection** | **String** |  | [optional] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::HarEntry.new(
  pageref: null,
  started_date_time: null,
  time: null,
  request: null,
  response: null,
  cache: null,
  timings: null,
  server_ip_address: null,
  _web_socket_messages: null,
  connection: null,
  comment: null
)
```

