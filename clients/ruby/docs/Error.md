# BrowserupMitmProxy::Error

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **name** | **String** | Name of the Error to add. Stored in har under _errors | [optional] |
| **details** | **String** | Short details of the error | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::Error.new(
  name: null,
  details: null
)
```

