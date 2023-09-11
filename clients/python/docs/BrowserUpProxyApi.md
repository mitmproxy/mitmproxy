# BrowserUpMitmProxyClient.BrowserUpProxyApi

All URIs are relative to *http://localhost:48088*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_counter**](BrowserUpProxyApi.md#add_counter) | **POST** /har/counters | 
[**add_error**](BrowserUpProxyApi.md#add_error) | **POST** /har/errors | 
[**get_har_log**](BrowserUpProxyApi.md#get_har_log) | **GET** /har | 
[**healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck | 
[**new_page**](BrowserUpProxyApi.md#new_page) | **POST** /har/page | 
[**reset_har_log**](BrowserUpProxyApi.md#reset_har_log) | **PUT** /har | 
[**verify_not_present**](BrowserUpProxyApi.md#verify_not_present) | **POST** /verify/not_present/{name} | 
[**verify_present**](BrowserUpProxyApi.md#verify_present) | **POST** /verify/present/{name} | 
[**verify_size**](BrowserUpProxyApi.md#verify_size) | **POST** /verify/size/{size}/{name} | 
[**verify_sla**](BrowserUpProxyApi.md#verify_sla) | **POST** /verify/sla/{time}/{name} | 


# **add_counter**
> add_counter(counter)



Add Custom Counter to the captured traffic har

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.counter import Counter
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)
    counter = BrowserUpMitmProxyClient.Counter() # Counter | Receives a new counter to add. The counter is stored, under the hood, in an array in the har under the _counters key

    try:
        api_instance.add_counter(counter)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->add_counter: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **counter** | [**Counter**](Counter.md)| Receives a new counter to add. The counter is stored, under the hood, in an array in the har under the _counters key | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: Not defined

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | The counter was added. |  -  |
**422** | The counter was invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **add_error**
> add_error(error)



Add Custom Error to the captured traffic har

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.error import Error
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)
    error = BrowserUpMitmProxyClient.Error() # Error | Receives an error to track. Internally, the error is stored in an array in the har under the _errors key

    try:
        api_instance.add_error(error)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->add_error: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **error** | [**Error**](Error.md)| Receives an error to track. Internally, the error is stored in an array in the har under the _errors key | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: Not defined

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | The Error was added. |  -  |
**422** | The Error was invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_har_log**
> Har get_har_log()



Get the current HAR.

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.har import Har
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)

    try:
        api_response = api_instance.get_har_log()
        print("The response of BrowserUpProxyApi->get_har_log:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->get_har_log: %s\n" % e)
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

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The current Har file. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **healthcheck**
> healthcheck()



Get the healthcheck

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)

    try:
        api_instance.healthcheck()
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->healthcheck: %s\n" % e)
```



### Parameters
This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | OK means all is well. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **new_page**
> Har new_page(title)



Starts a fresh HAR Page (Step) in the current active HAR to group requests.

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.har import Har
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)
    title = 'title_example' # str | The unique title for this har page/step.

    try:
        api_response = api_instance.new_page(title)
        print("The response of BrowserUpProxyApi->new_page:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->new_page: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **title** | **str**| The unique title for this har page/step. | 

### Return type

[**Har**](Har.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The current Har file. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reset_har_log**
> Har reset_har_log()



Starts a fresh HAR capture session.

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.har import Har
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)

    try:
        api_response = api_instance.reset_har_log()
        print("The response of BrowserUpProxyApi->reset_har_log:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->reset_har_log: %s\n" % e)
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

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The current Har file. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **verify_not_present**
> VerifyResult verify_not_present(name, match_criteria)



Verify no matching items are present in the captured traffic

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.match_criteria import MatchCriteria
from BrowserUpMitmProxyClient.models.verify_result import VerifyResult
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)
    name = 'name_example' # str | The unique name for this verification operation
    match_criteria = BrowserUpMitmProxyClient.MatchCriteria() # MatchCriteria | Match criteria to select requests - response pairs for size tests

    try:
        api_response = api_instance.verify_not_present(name, match_criteria)
        print("The response of BrowserUpProxyApi->verify_not_present:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->verify_not_present: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**| The unique name for this verification operation | 
 **match_criteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The traffic had no matching items |  -  |
**422** | The MatchCriteria are invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **verify_present**
> VerifyResult verify_present(name, match_criteria)



Verify at least one matching item is present in the captured traffic

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.match_criteria import MatchCriteria
from BrowserUpMitmProxyClient.models.verify_result import VerifyResult
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)
    name = 'name_example' # str | The unique name for this verification operation
    match_criteria = BrowserUpMitmProxyClient.MatchCriteria() # MatchCriteria | Match criteria to select requests - response pairs for size tests

    try:
        api_response = api_instance.verify_present(name, match_criteria)
        print("The response of BrowserUpProxyApi->verify_present:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->verify_present: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**| The unique name for this verification operation | 
 **match_criteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The traffic conformed to the time criteria. |  -  |
**422** | The MatchCriteria are invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **verify_size**
> VerifyResult verify_size(size, name, match_criteria)



Verify matching items in the captured traffic meet the size criteria

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.match_criteria import MatchCriteria
from BrowserUpMitmProxyClient.models.verify_result import VerifyResult
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)
    size = 56 # int | The size used for comparison, in kilobytes
    name = 'name_example' # str | The unique name for this verification operation
    match_criteria = BrowserUpMitmProxyClient.MatchCriteria() # MatchCriteria | Match criteria to select requests - response pairs for size tests

    try:
        api_response = api_instance.verify_size(size, name, match_criteria)
        print("The response of BrowserUpProxyApi->verify_size:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->verify_size: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **size** | **int**| The size used for comparison, in kilobytes | 
 **name** | **str**| The unique name for this verification operation | 
 **match_criteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The traffic conformed to the size criteria. |  -  |
**422** | The MatchCriteria are invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **verify_sla**
> VerifyResult verify_sla(time, name, match_criteria)



Verify each traffic item matching the criteria meets is below SLA time

### Example

```python
import time
import os
import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.models.match_criteria import MatchCriteria
from BrowserUpMitmProxyClient.models.verify_result import VerifyResult
from BrowserUpMitmProxyClient.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:48088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpMitmProxyClient.Configuration(
    host = "http://localhost:48088"
)


# Enter a context with an instance of the API client
with BrowserUpMitmProxyClient.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = BrowserUpMitmProxyClient.BrowserUpProxyApi(api_client)
    time = 56 # int | The time used for comparison
    name = 'name_example' # str | The unique name for this verification operation
    match_criteria = BrowserUpMitmProxyClient.MatchCriteria() # MatchCriteria | Match criteria to select requests - response pairs for size tests

    try:
        api_response = api_instance.verify_sla(time, name, match_criteria)
        print("The response of BrowserUpProxyApi->verify_sla:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BrowserUpProxyApi->verify_sla: %s\n" % e)
```



### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **time** | **int**| The time used for comparison | 
 **name** | **str**| The unique name for this verification operation | 
 **match_criteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The traffic conformed to the time criteria. |  -  |
**422** | The MatchCriteria are invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

