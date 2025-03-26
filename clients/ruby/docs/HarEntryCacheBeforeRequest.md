# BrowserupMitmProxy::HarEntryCacheBeforeRequest

## Class instance methods

### `openapi_one_of`

Returns the list of classes defined in oneOf.

#### Example

```ruby
require 'browserup_mitmproxy_client'

BrowserupMitmProxy::HarEntryCacheBeforeRequest.openapi_one_of
# =>
# [
#   :'HarEntryCacheBeforeRequestOneOf',
#   :'Null'
# ]
```

### build

Find the appropriate object from the `openapi_one_of` list and casts the data into it.

#### Example

```ruby
require 'browserup_mitmproxy_client'

BrowserupMitmProxy::HarEntryCacheBeforeRequest.build(data)
# => #<HarEntryCacheBeforeRequestOneOf:0x00007fdd4aab02a0>

BrowserupMitmProxy::HarEntryCacheBeforeRequest.build(data_that_doesnt_match)
# => nil
```

#### Parameters

| Name | Type | Description |
| ---- | ---- | ----------- |
| **data** | **Mixed** | data to be matched against the list of oneOf items |

#### Return type

- `HarEntryCacheBeforeRequestOneOf`
- `Null`
- `nil` (if no type matches)

