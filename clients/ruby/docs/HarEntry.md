# BrowserupMitmProxy::HarEntry

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **pageref** | **Object** |  | [optional] |
| **started_date_time** | **Object** |  |  |
| **time** | **Object** |  |  |
| **request** | [**HarEntryRequest**](HarEntryRequest.md) |  |  |
| **response** | [**HarEntryResponse**](HarEntryResponse.md) |  |  |
| **cache** | [**HarEntryCache**](HarEntryCache.md) |  |  |
| **timings** | [**HarEntryTimings**](HarEntryTimings.md) |  |  |
| **server_ip_address** | **Object** |  | [optional] |
| **_web_socket_messages** | **Object** |  | [optional] |
| **connection** | **Object** |  | [optional] |
| **comment** | **Object** |  | [optional] |

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

