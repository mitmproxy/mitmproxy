# BrowserupProxyClient::ProxyApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
| ------ | ------------ | ----------- |
| [**allowlist_delete**](ProxyApi.md#allowlist_delete) | **DELETE** /allowlist |  |
| [**allowlist_get**](ProxyApi.md#allowlist_get) | **GET** /allowlist |  |
| [**allowlist_post**](ProxyApi.md#allowlist_post) | **POST** /allowlist |  |
| [**blocklist_get**](ProxyApi.md#blocklist_get) | **GET** /blocklist |  |
| [**blocklist_post**](ProxyApi.md#blocklist_post) | **POST** /blocklist |  |


## allowlist_delete

> allowlist_delete



Deletes the AllowList, which will turn-off allowlist based filtering

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxyClient::ProxyApi.new

begin
  
  api_instance.allowlist_delete
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->allowlist_delete: #{e}"
end
```

#### Using the allowlist_delete_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> allowlist_delete_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.allowlist_delete_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->allowlist_delete_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

nil (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: Not defined


## allowlist_get

> <AllowList> allowlist_get



Get an AllowList

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxyClient::ProxyApi.new

begin
  
  result = api_instance.allowlist_get
  p result
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->allowlist_get: #{e}"
end
```

#### Using the allowlist_get_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<AllowList>, Integer, Hash)> allowlist_get_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.allowlist_get_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <AllowList>
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->allowlist_get_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**AllowList**](AllowList.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## allowlist_post

> allowlist_post(opts)



Sets an AllowList

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxyClient::ProxyApi.new
opts = {
  allow_list: BrowserupProxyClient::AllowList.new({status_code: 'status_code_example', url_pattern: 'url_pattern_example'}) # AllowList | 
}

begin
  
  api_instance.allowlist_post(opts)
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->allowlist_post: #{e}"
end
```

#### Using the allowlist_post_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> allowlist_post_with_http_info(opts)

```ruby
begin
  
  data, status_code, headers = api_instance.allowlist_post_with_http_info(opts)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->allowlist_post_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **allow_list** | [**AllowList**](AllowList.md) |  | [optional] |

### Return type

nil (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined


## blocklist_get

> <BlockList> blocklist_get



Get a blocklist

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxyClient::ProxyApi.new

begin
  
  result = api_instance.blocklist_get
  p result
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->blocklist_get: #{e}"
end
```

#### Using the blocklist_get_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<BlockList>, Integer, Hash)> blocklist_get_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.blocklist_get_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <BlockList>
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->blocklist_get_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**BlockList**](BlockList.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## blocklist_post

> blocklist_post(opts)



Sets an BlockList

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxyClient::ProxyApi.new
opts = {
  block_list: BrowserupProxyClient::BlockList.new({status_code: 'status_code_example', url_pattern: 'url_pattern_example', http_method_pattern: 'http_method_pattern_example'}) # BlockList | 
}

begin
  
  api_instance.blocklist_post(opts)
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->blocklist_post: #{e}"
end
```

#### Using the blocklist_post_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> blocklist_post_with_http_info(opts)

```ruby
begin
  
  data, status_code, headers = api_instance.blocklist_post_with_http_info(opts)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxyClient::ApiError => e
  puts "Error when calling ProxyApi->blocklist_post_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **block_list** | [**BlockList**](BlockList.md) |  | [optional] |

### Return type

nil (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined

