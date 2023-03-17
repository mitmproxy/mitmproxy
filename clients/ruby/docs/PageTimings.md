# BrowserupMitmProxy::PageTimings

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **on_content_load** | **Object** |  |  |
| **on_load** | **Object** |  |  |
| **_href** | **Object** |  | [optional] |
| **_dns** | **Object** |  | [optional] |
| **_ssl** | **Object** |  | [optional] |
| **_ttfb** | **Object** |  | [optional] |
| **_cumulative_layout_shift** | **Object** |  | [optional] |
| **_largest_contentful_paint** | **Object** |  | [optional] |
| **_first_paint** | **Object** |  | [optional] |
| **_first_input_delay** | **Object** |  | [optional] |
| **_dom_interactive** | **Object** |  | [optional] |
| **_first_contentful_paint** | **Object** |  | [optional] |
| **comment** | **Object** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::PageTimings.new(
  on_content_load: null,
  on_load: null,
  _href: null,
  _dns: null,
  _ssl: null,
  _ttfb: null,
  _cumulative_layout_shift: null,
  _largest_contentful_paint: null,
  _first_paint: null,
  _first_input_delay: null,
  _dom_interactive: null,
  _first_contentful_paint: null,
  comment: null
)
```

