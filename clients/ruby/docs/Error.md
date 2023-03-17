# BrowserupMitmProxy::Error

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **details** | **String** | Short details of the error | [optional] |
| **name** | **String** | Name of the Error to add. Stored in har under _errors | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::Error.new(
  details: null,
  name: null
)
```

