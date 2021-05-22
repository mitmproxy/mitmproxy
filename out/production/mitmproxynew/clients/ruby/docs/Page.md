# BrowserupProxy::Page

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **started_date_time** | **Time** |  |  |
| **id** | **String** |  |  |
| **title** | **String** |  |  |
| **page_timings** | [**PagePageTimings**](PagePageTimings.md) |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::Page.new(
  started_date_time: null,
  id: null,
  title: null,
  page_timings: null,
  comment: null
)
```

