# BrowserupMitmProxy::Error

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **name** | **Object** | Name of the Error to add. Stored in har under _errors | [optional] |
| **details** | **Object** | Short details of the error | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::Error.new(
  name: null,
  details: null
)
```

