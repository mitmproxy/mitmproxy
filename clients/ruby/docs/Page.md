# BrowserupMitmProxy::Page

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **started_date_time** | **Object** |  |  |
| **id** | **Object** |  |  |
| **title** | **Object** |  |  |
| **_verifications** | **Object** |  | [optional] |
| **_counters** | **Object** |  | [optional] |
| **_errors** | **Object** |  | [optional] |
| **page_timings** | [**PageTimings**](PageTimings.md) |  |  |
| **comment** | **Object** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::Page.new(
  started_date_time: null,
  id: null,
  title: null,
  _verifications: null,
  _counters: null,
  _errors: null,
  page_timings: null,
  comment: null
)
```

