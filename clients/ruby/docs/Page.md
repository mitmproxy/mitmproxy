# BrowserupMitmProxy::Page

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **started_date_time** | **Time** |  |  |
| **id** | **String** |  |  |
| **title** | **String** |  |  |
| **_verifications** | [**Array&lt;VerifyResult&gt;**](VerifyResult.md) |  | [optional] |
| **_metrics** | [**Array&lt;Metric&gt;**](Metric.md) |  | [optional] |
| **_errors** | [**Array&lt;Error&gt;**](Error.md) |  | [optional] |
| **page_timings** | [**PageTimings**](PageTimings.md) |  |  |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::Page.new(
  started_date_time: null,
  id: null,
  title: null,
  _verifications: null,
  _metrics: null,
  _errors: null,
  page_timings: null,
  comment: null
)
```

