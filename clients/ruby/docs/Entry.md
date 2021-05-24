# BrowserupProxy::Entry

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **pageref** | **String** |  | [optional] |
| **started_date_time** | **String** |  |  |
| **time** | **Float** |  |  |
| **request** | [**EntryRequest**](EntryRequest.md) |  |  |
| **response** | [**EntryResponse**](EntryResponse.md) |  |  |
| **cache** | **Object** |  |  |
| **timings** | **Object** |  |  |
| **server_ip_address** | **String** |  | [optional] |
| **connection** | **String** |  | [optional] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::Entry.new(
  pageref: null,
  started_date_time: null,
  time: null,
  request: null,
  response: null,
  cache: null,
  timings: null,
  server_ip_address: null,
  connection: null,
  comment: null
)
```

