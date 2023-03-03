# BrowserupMitmProxy::EntryCacheBeforeRequest

## Class instance methods

### `openapi_one_of`

Returns the list of classes defined in oneOf.

#### Example

```ruby
require 'browserup_mitmproxy_client'

BrowserupMitmProxy::EntryCacheBeforeRequest.openapi_one_of
# =>
# [
#   :'EntryCacheBeforeRequestOneOf',
#   :'Null'
# ]
```

### build

Find the appropriate object from the `openapi_one_of` list and casts the data into it.

#### Example

```ruby
require 'browserup_mitmproxy_client'

BrowserupMitmProxy::EntryCacheBeforeRequest.build(data)
# => #<EntryCacheBeforeRequestOneOf:0x00007fdd4aab02a0>

BrowserupMitmProxy::EntryCacheBeforeRequest.build(data_that_doesnt_match)
# => nil
```

#### Parameters

| Name | Type | Description |
| ---- | ---- | ----------- |
| **data** | **Mixed** | data to be matched against the list of oneOf items |

#### Return type

- `EntryCacheBeforeRequestOneOf`
- `Null`
- `nil` (if no type matches)

