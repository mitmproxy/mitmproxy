# BrowserupProxy::BrowserUpProxyApi

All URIs are relative to *http://localhost:8088*

| Method | HTTP request | Description |
| ------ | ------------ | ----------- |
| [**add_custom_har_fields**](BrowserUpProxyApi.md#add_custom_har_fields) | **PUT** /har/page |  |
| [**get_har_log**](BrowserUpProxyApi.md#get_har_log) | **GET** /har |  |
| [**healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck |  |
| [**reset_har_log**](BrowserUpProxyApi.md#reset_har_log) | **PUT** /har |  |
| [**set_har_page**](BrowserUpProxyApi.md#set_har_page) | **POST** /har/page |  |
| [**verify_not_present**](BrowserUpProxyApi.md#verify_not_present) | **POST** /verify/not_present |  |
| [**verify_present**](BrowserUpProxyApi.md#verify_present) | **POST** /verify/present |  |
| [**verify_size**](BrowserUpProxyApi.md#verify_size) | **POST** /verify/size/{size} |  |
| [**verify_sla**](BrowserUpProxyApi.md#verify_sla) | **POST** /verify/sla/{time} |  |


## add_custom_har_fields

> add_custom_har_fields(opts)



Add custom fields to the current HAR.

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
opts = {
  body: Object # Object | 
}

begin
  
  api_instance.add_custom_har_fields(opts)
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->add_custom_har_fields: #{e}"
end
```

#### Using the add_custom_har_fields_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> add_custom_har_fields_with_http_info(opts)

```ruby
begin
  
  data, status_code, headers = api_instance.add_custom_har_fields_with_http_info(opts)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->add_custom_har_fields_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **body** | **Object** |  | [optional] |

### Return type

nil (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined


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


## healthcheck

> healthcheck



Get the healthcheck

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new

begin
  
  api_instance.healthcheck
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->healthcheck: #{e}"
end
```

#### Using the healthcheck_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> healthcheck_with_http_info

```ruby
begin
  
  data, status_code, headers = api_instance.healthcheck_with_http_info
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->healthcheck_with_http_info: #{e}"
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


## verify_not_present

> <VerifyResult> verify_not_present(match_criteria)



Verify no matching items are present in the captured traffic

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
match_criteria = BrowserupProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_not_present(match_criteria)
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_not_present: #{e}"
end
```

#### Using the verify_not_present_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_not_present_with_http_info(match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_not_present_with_http_info(match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_not_present_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verify_present

> <VerifyResult> verify_present(match_criteria)



Verify at least one matching item is present in the captured traffic

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
match_criteria = BrowserupProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_present(match_criteria)
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_present: #{e}"
end
```

#### Using the verify_present_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_present_with_http_info(match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_present_with_http_info(match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_present_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verify_size

> <VerifyResult> verify_size(size, match_criteria)



Verify matching items in the captured traffic meet the size criteria

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
size = 56 # Integer | The size used for comparison
match_criteria = BrowserupProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_size(size, match_criteria)
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_size: #{e}"
end
```

#### Using the verify_size_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_size_with_http_info(size, match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_size_with_http_info(size, match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_size_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **size** | **Integer** | The size used for comparison |  |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verify_sla

> <VerifyResult> verify_sla(time, match_criteria)



Verify each traffic item matching the criteria meets is below SLA time

### Examples

```ruby
require 'time'
require 'browserup_proxy_client'

api_instance = BrowserupProxy::BrowserUpProxyApi.new
time = 56 # Integer | The time used for comparison
match_criteria = BrowserupProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_sla(time, match_criteria)
  p result
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_sla: #{e}"
end
```

#### Using the verify_sla_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_sla_with_http_info(time, match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_sla_with_http_info(time, match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_sla_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **time** | **Integer** | The time used for comparison |  |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

