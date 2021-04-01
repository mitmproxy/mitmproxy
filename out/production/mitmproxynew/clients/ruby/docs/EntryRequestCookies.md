# BrowserupProxy::EntryRequestCookies

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **name** | **String** |  |  |
| **value** | **String** |  |  |
| **path** | **String** |  | [optional] |
| **domain** | **String** |  | [optional] |
| **expires** | **String** |  | [optional] |
| **http_only** | **Boolean** |  | [optional] |
| **secure** | **Boolean** |  | [optional] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_proxy_client'

instance = BrowserupProxy::EntryRequestCookies.new(
  name: null,
  value: null,
  path: null,
  domain: null,
  expires: null,
  http_only: null,
  secure: null,
  comment: null
)
```

