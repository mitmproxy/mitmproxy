# BrowserupMitmProxy::PageTiming

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **name** | **String** | Name of Custom Counter value you are adding to the page under counters |  |
| **on_content_load** | **Float** | onContentLoad per the browser |  |
| **_first_paint** | **Float** | firstPaint from the browser |  |
| **_dns** | **Float** | dns lookup time from the browser |  |
| **_ssl** | **Float** | Ssl connect time from the browser |  |
| **_first_contentful_paint** | **Float** | firstContentfulPaint from the browser |  |
| **_cumulative_layout_shift** | **Float** | cumulativeLayoutShift metric from the browser |  |
| **_ttfb** | **Float** | Time to first byte of the page&#39;s first request per the browser |  |
| **value** | **Float** | Value for the counter |  |
| **_first_input_delay** | **Float** | firstInputDelay from the browser |  |
| **_largest_content_full_paint** | **Float** | largestContentFullPaint from the browser |  |
| **on_load** | **Float** | onLoad per the browser |  |
| **_dom_interactive** | **Float** | domInteractive from the browser |  |
| **_href** | **String** | Top level href, including hashtag, etc per the browser |  |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::PageTiming.new(
  name: null,
  on_content_load: null,
  _first_paint: null,
  _dns: null,
  _ssl: null,
  _first_contentful_paint: null,
  _cumulative_layout_shift: null,
  _ttfb: null,
  value: null,
  _first_input_delay: null,
  _largest_content_full_paint: null,
  on_load: null,
  _dom_interactive: null,
  _href: null
)
```

