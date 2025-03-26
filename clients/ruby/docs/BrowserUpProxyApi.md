# BrowserupMitmProxy::BrowserUpProxyApi

All URIs are relative to *http://localhost:48088*

| Method | HTTP request | Description |
| ------ | ------------ | ----------- |
| [**add_error**](BrowserUpProxyApi.md#add_error) | **POST** /har/errors |  |
| [**add_metric**](BrowserUpProxyApi.md#add_metric) | **POST** /har/metrics |  |
| [**get_har_log**](BrowserUpProxyApi.md#get_har_log) | **GET** /har |  |
| [**healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck |  |
| [**new_page**](BrowserUpProxyApi.md#new_page) | **POST** /har/page |  |
| [**reset_har_log**](BrowserUpProxyApi.md#reset_har_log) | **PUT** /har |  |
| [**verify_not_present**](BrowserUpProxyApi.md#verify_not_present) | **POST** /verify/not_present/{name} |  |
| [**verify_present**](BrowserUpProxyApi.md#verify_present) | **POST** /verify/present/{name} |  |
| [**verify_size**](BrowserUpProxyApi.md#verify_size) | **POST** /verify/size/{size}/{name} |  |
| [**verify_sla**](BrowserUpProxyApi.md#verify_sla) | **POST** /verify/sla/{time}/{name} |  |


## add_error

> add_error(error)



Add Custom Error to the captured traffic har

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
error = BrowserupMitmProxy::Error.new # Error | Receives an error to track. Internally, the error is stored in an array in the har under the _errors key

begin
  
  api_instance.add_error(error)
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->add_error: #{e}"
end
```

#### Using the add_error_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> add_error_with_http_info(error)

```ruby
begin
  
  data, status_code, headers = api_instance.add_error_with_http_info(error)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->add_error_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **error** | [**Error**](Error.md) | Receives an error to track. Internally, the error is stored in an array in the har under the _errors key |  |

### Return type

nil (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined


## add_metric

> add_metric(metric)



Add Custom Metric to the captured traffic har

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
metric = BrowserupMitmProxy::Metric.new # Metric | Receives a new metric to add. The metric is stored, under the hood, in an array in the har under the _metrics key

begin
  
  api_instance.add_metric(metric)
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->add_metric: #{e}"
end
```

#### Using the add_metric_with_http_info variant

This returns an Array which contains the response data (`nil` in this case), status code and headers.

> <Array(nil, Integer, Hash)> add_metric_with_http_info(metric)

```ruby
begin
  
  data, status_code, headers = api_instance.add_metric_with_http_info(metric)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => nil
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->add_metric_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **metric** | [**Metric**](Metric.md) | Receives a new metric to add. The metric is stored, under the hood, in an array in the har under the _metrics key |  |

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
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.get_har_log
  p result
rescue BrowserupMitmProxy::ApiError => e
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
rescue BrowserupMitmProxy::ApiError => e
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
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new

begin
  
  api_instance.healthcheck
rescue BrowserupMitmProxy::ApiError => e
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
rescue BrowserupMitmProxy::ApiError => e
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


## new_page

> <Har> new_page(title)



Starts a fresh HAR Page (Step) in the current active HAR to group requests.

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
title = 'title_example' # String | The unique title for this har page/step.

begin
  
  result = api_instance.new_page(title)
  p result
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->new_page: #{e}"
end
```

#### Using the new_page_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<Har>, Integer, Hash)> new_page_with_http_info(title)

```ruby
begin
  
  data, status_code, headers = api_instance.new_page_with_http_info(title)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <Har>
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->new_page_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **title** | **String** | The unique title for this har page/step. |  |

### Return type

[**Har**](Har.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## reset_har_log

> <Har> reset_har_log



Starts a fresh HAR capture session.

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new

begin
  
  result = api_instance.reset_har_log
  p result
rescue BrowserupMitmProxy::ApiError => e
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
rescue BrowserupMitmProxy::ApiError => e
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


## verify_not_present

> <VerifyResult> verify_not_present(name, match_criteria)



Verify no matching items are present in the captured traffic

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
name = 'name_example' # String | The unique name for this verification operation
match_criteria = BrowserupMitmProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_not_present(name, match_criteria)
  p result
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_not_present: #{e}"
end
```

#### Using the verify_not_present_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_not_present_with_http_info(name, match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_not_present_with_http_info(name, match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_not_present_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **name** | **String** | The unique name for this verification operation |  |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verify_present

> <VerifyResult> verify_present(name, match_criteria)



Verify at least one matching item is present in the captured traffic

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
name = 'name_example' # String | The unique name for this verification operation
match_criteria = BrowserupMitmProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_present(name, match_criteria)
  p result
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_present: #{e}"
end
```

#### Using the verify_present_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_present_with_http_info(name, match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_present_with_http_info(name, match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_present_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **name** | **String** | The unique name for this verification operation |  |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verify_size

> <VerifyResult> verify_size(size, name, match_criteria)



Verify matching items in the captured traffic meet the size criteria

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
size = 56 # Integer | The size used for comparison, in kilobytes
name = 'name_example' # String | The unique name for this verification operation
match_criteria = BrowserupMitmProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_size(size, name, match_criteria)
  p result
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_size: #{e}"
end
```

#### Using the verify_size_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_size_with_http_info(size, name, match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_size_with_http_info(size, name, match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_size_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **size** | **Integer** | The size used for comparison, in kilobytes |  |
| **name** | **String** | The unique name for this verification operation |  |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verify_sla

> <VerifyResult> verify_sla(time, name, match_criteria)



Verify each traffic item matching the criteria meets is below SLA time

### Examples

```ruby
require 'time'
require 'browserup_mitmproxy_client'

api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
time = 56 # Integer | The time used for comparison
name = 'name_example' # String | The unique name for this verification operation
match_criteria = BrowserupMitmProxy::MatchCriteria.new # MatchCriteria | Match criteria to select requests - response pairs for size tests

begin
  
  result = api_instance.verify_sla(time, name, match_criteria)
  p result
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_sla: #{e}"
end
```

#### Using the verify_sla_with_http_info variant

This returns an Array which contains the response data, status code and headers.

> <Array(<VerifyResult>, Integer, Hash)> verify_sla_with_http_info(time, name, match_criteria)

```ruby
begin
  
  data, status_code, headers = api_instance.verify_sla_with_http_info(time, name, match_criteria)
  p status_code # => 2xx
  p headers # => { ... }
  p data # => <VerifyResult>
rescue BrowserupMitmProxy::ApiError => e
  puts "Error when calling BrowserUpProxyApi->verify_sla_with_http_info: #{e}"
end
```

### Parameters

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **time** | **Integer** | The time used for comparison |  |
| **name** | **String** | The unique name for this verification operation |  |
| **match_criteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

