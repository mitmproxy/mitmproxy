# BrowserupProxy::BrowserUpProxyApi

All URIs are relative to *http://localhost:8080*

| Method | HTTP request | Description |
| ------ | ------------ | ----------- |
| [**clear_additional_headers**](BrowserUpProxyApi.md#clear_additional_headers) | **DELETE** /additional_headers |  |
| [**clear_allow_list**](BrowserUpProxyApi.md#clear_allow_list) | **DELETE** /allowlist |  |
| [**clear_basic_auth_settings**](BrowserUpProxyApi.md#clear_basic_auth_settings) | **DELETE** /auth_basic/{domain} |  |
| [**get_additional_headers**](BrowserUpProxyApi.md#get_additional_headers) | **GET** /additional_headers |  |
| [**get_allow_list**](BrowserUpProxyApi.md#get_allow_list) | **GET** /allowlist |  |
| [**get_block_list**](BrowserUpProxyApi.md#get_block_list) | **GET** /blocklist |  |
| [**get_har_log**](BrowserUpProxyApi.md#get_har_log) | **GET** /har |  |
| [**healthcheck_get**](BrowserUpProxyApi.md#healthcheck_get) | **GET** /healthcheck |  |
| [**reset_har_log**](BrowserUpProxyApi.md#reset_har_log) | **PUT** /har |  |
| [**set_additional_headers**](BrowserUpProxyApi.md#set_additional_headers) | **POST** /additional_headers |  |
| [**set_allow_list**](BrowserUpProxyApi.md#set_allow_list) | **POST** /allowlist |  |
| [**set_basic_auth**](BrowserUpProxyApi.md#set_basic_auth) | **POST** /auth_basic/{domain} |  |
| [**set_block_list**](BrowserUpProxyApi.md#set_block_list) | **POST** /blocklist |  |
| [**set_har_page**](BrowserUpProxyApi.md#set_har_page) | **PUT** /har/page |  |


## clear_additional_headers

> clear_additional_headers



Clear the additional Headers

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  api_instance.clear_additional_headers
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->clear_additional_headers: #{e}"
end
```

#### Using the clear_additional_headers_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> clear_additional_headers_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.clear_additional_headers_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->clear_additional_headers_with_http_info: #{e}"
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


## clear_allow_list

> clear_allow_list



Clears the AllowList, which will turn-off allowlist based filtering

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  api_instance.clear_allow_list
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->clear_allow_list: #{e}"
end
```

#### Using the clear_allow_list_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> clear_allow_list_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.clear_allow_list_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->clear_allow_list_with_http_info: #{e}"
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


## clear_basic_auth_settings

> clear_basic_auth_settings(domain)



Clears Basic Auth for a domain, disabling Automatic Basic Auth for it.

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
domain = 'domain_example' # String | The domain for which to clear the basic auth settings

begin
  
  api_instance.clear_basic_auth_settings(domain)
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->clear_basic_auth_settings: #{e}"
end
```

#### Using the clear_basic_auth_settings_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> clear_basic_auth_settings_with_http_info(domain)

```ruby
begin
  
  data, status_code, headers = api_instance.clear_basic_auth_settings_with_http_info(domain)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->clear_basic_auth_settings_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **domain** | **String** | The domain for which to clear the basic auth settings |  |

### Return type

nil (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: Not defined


## get_additional_headers

> <Headers> get_additional_headers



Get the current added Headers

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.get_additional_headers
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_additional_headers: #{e}"
end
```

#### Using the get_additional_headers_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<Headers>, Integer, Hash)> get_additional_headers_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.get_additional_headers_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <Headers>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_additional_headers_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Headers**](Headers.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## get_allow_list

> <AllowList> get_allow_list



Get an AllowList

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.get_allow_list
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_allow_list: #{e}"
end
```

#### Using the get_allow_list_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<AllowList>, Integer, Hash)> get_allow_list_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.get_allow_list_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <AllowList>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_allow_list_with_http_info: #{e}"
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


## get_block_list

> <BlockList> get_block_list



Get a blocklist

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.get_block_list
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_block_list: #{e}"
end
```

#### Using the get_block_list_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<BlockList>, Integer, Hash)> get_block_list_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.get_block_list_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <BlockList>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_block_list_with_http_info: #{e}"
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


## get_har_log

> <Har> get_har_log



Get the current HAR.

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.get_har_log
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_har_log: #{e}"
end
```

#### Using the get_har_log_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<Har>, Integer, Hash)> get_har_log_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.get_har_log_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <Har>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->get_har_log_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Har**](Har.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## healthcheck_get

> healthcheck_get



Get the healthcheck

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  api_instance.healthcheck_get
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->healthcheck_get: #{e}"
end
```

#### Using the healthcheck_get_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> healthcheck_get_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.healthcheck_get_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->healthcheck_get_with_http_info: #{e}"
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


## reset_har_log

> <Har> reset_har_log



Starts a fresh HAR capture session.

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.reset_har_log
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->reset_har_log: #{e}"
end
```

#### Using the reset_har_log_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<Har>, Integer, Hash)> reset_har_log_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.reset_har_log_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <Har>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->reset_har_log_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Har**](Har.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## set_additional_headers

> <Headers> set_additional_headers



Set additional headers to add to requests

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.set_additional_headers
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_additional_headers: #{e}"
end
```

#### Using the set_additional_headers_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<Headers>, Integer, Hash)> set_additional_headers_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.set_additional_headers_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <Headers>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_additional_headers_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Headers**](Headers.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## set_allow_list

> set_allow_list(opts)



Sets an AllowList

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
opts = {
  allow_list: BrowserupProxy::AllowList.new({status_code: 'status_code_example', url_pattern: 'url_pattern_example'}) # AllowList | 
}

begin
  
  api_instance.set_allow_list(opts)
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_allow_list: #{e}"
end
```

#### Using the set_allow_list_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> set_allow_list_with_http_info(opts)

```ruby
begin
  
  data, status_code, headers = api_instance.set_allow_list_with_http_info(opts)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_allow_list_with_http_info: #{e}"
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


## set_basic_auth

> set_basic_auth(domain, opts)



Enables automatic basic auth for a domain

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
domain = 'domain_example' # String | The domain for which this Basic Auth should be used
opts = {
  auth_basic: BrowserupProxy::AuthBasic.new({base_64_credentials: 'base_64_credentials_example'}) # AuthBasic | 
}

begin
  
  api_instance.set_basic_auth(domain, opts)
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_basic_auth: #{e}"
end
```

#### Using the set_basic_auth_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> set_basic_auth_with_http_info(domain, opts)

```ruby
begin
  
  data, status_code, headers = api_instance.set_basic_auth_with_http_info(domain, opts)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_basic_auth_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **domain** | **String** | The domain for which this Basic Auth should be used |  |
| **auth_basic** | [**AuthBasic**](AuthBasic.md) |  | [optional] |

### Return type

nil (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined


## set_block_list

> set_block_list(opts)



Sets an BlockList

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
opts = {
  block_list: BrowserupProxy::BlockList.new({http_method_pattern: 'http_method_pattern_example', status_code: 'status_code_example', url_pattern: 'url_pattern_example'}) # BlockList | 
}

begin
  
  api_instance.set_block_list(opts)
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_block_list: #{e}"
end
```

#### Using the set_block_list_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> set_block_list_with_http_info(opts)

```ruby
begin
  
  data, status_code, headers = api_instance.set_block_list_with_http_info(opts)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_block_list_with_http_info: #{e}"
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


## set_har_page

> <Har> set_har_page



Starts a fresh HAR Page in the current active HAR

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.set_har_page
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_har_page: #{e}"
end
```

#### Using the set_har_page_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<Har>, Integer, Hash)> set_har_page_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.set_har_page_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <Har>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->set_har_page_with_http_info: #{e}"
end
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Har**](Har.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

