# BrowserupMitmProxy::PageTiming

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **on_content_load** | **Float** | onContentLoad per the browser | [optional] |
| **on_load** | **Float** | onLoad per the browser | [optional] |
| **_first_input_delay** | **Float** | firstInputDelay from the browser | [optional] |
| **_first_paint** | **Float** | firstPaint from the browser | [optional] |
| **_cumulative_layout_shift** | **Float** | cumulativeLayoutShift metric from the browser | [optional] |
| **_largest_contentful_paint** | **Float** | largestContentfulPaint from the browser | [optional] |
| **_dom_interactive** | **Float** | domInteractive from the browser | [optional] |
| **_first_contentful_paint** | **Float** | firstContentfulPaint from the browser | [optional] |
| **_dns** | **Float** | dns lookup time from the browser | [optional] |
| **_ssl** | **Float** | Ssl connect time from the browser | [optional] |
| **_time_to_first_byte** | **Float** | Time to first byte of the page&#39;s first request per the browser | [optional] |
| **_href** | **String** | Top level href, including hashtag, etc per the browser | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::PageTiming.new(
  on_content_load: null,
  on_load: null,
  _first_input_delay: null,
  _first_paint: null,
  _cumulative_layout_shift: null,
  _largest_contentful_paint: null,
  _dom_interactive: null,
  _first_contentful_paint: null,
  _dns: null,
  _ssl: null,
  _time_to_first_byte: null,
  _href: null
)
```

