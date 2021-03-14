# BrowserupProxy::AllowList

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **status_code** | **String** | HTTP Status Code to match |  |
| **url_pattern** | **String** | URL Regex Pattern to match |  |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::AllowList.new(
  status_code: null,
  url_pattern: null
)
```

