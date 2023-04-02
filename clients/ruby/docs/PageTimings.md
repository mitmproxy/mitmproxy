# BrowserupMitmProxy::PageTimings

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **on_content_load** | **Integer** |  | [default to -1] |
| **on_load** | **Integer** |  | [default to -1] |
| **_href** | **String** |  | [optional][default to &#39;&#39;] |
| **_dns** | **Integer** |  | [optional][default to -1] |
| **_ssl** | **Integer** |  | [optional][default to -1] |
| **_time_to_first_byte** | **Integer** |  | [optional][default to -1] |
| **_cumulative_layout_shift** | **Float** |  | [optional][default to -1] |
| **_largest_contentful_paint** | [**LargestContentfulPaint**](LargestContentfulPaint.md) |  | [optional] |
| **_first_paint** | **Integer** |  | [optional][default to -1] |
| **_first_input_delay** | **Float** |  | [optional][default to -1] |
| **_dom_interactive** | **Integer** |  | [optional][default to -1] |
| **_first_contentful_paint** | **Integer** |  | [optional][default to -1] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::PageTimings.new(
  on_content_load: null,
  on_load: null,
  _href: null,
  _dns: null,
  _ssl: null,
  _time_to_first_byte: null,
  _cumulative_layout_shift: null,
  _largest_contentful_paint: null,
  _first_paint: null,
  _first_input_delay: null,
  _dom_interactive: null,
  _first_contentful_paint: null,
  comment: null
)
```

