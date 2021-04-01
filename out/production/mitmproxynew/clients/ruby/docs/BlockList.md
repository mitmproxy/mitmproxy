# BrowserupProxy::BlockList

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **http_method_pattern** | **String** | HTTP Method Regex Pattern |  |
| **status_code** | **String** | HTTP Status Code |  |
| **url_pattern** | **String** | URL Regex Pattern |  |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::BlockList.new(
  http_method_pattern: null,
  status_code: null,
  url_pattern: null
)
```

