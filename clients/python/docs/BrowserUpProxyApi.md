# BrowserUpProxyClient.BrowserUpProxyApi

All URIs are relative to *http://localhost:8088*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_custom_har_fields**](BrowserUpProxyApi.md#add_custom_har_fields) | **PUT** /har/page | 
[**get_har_log**](BrowserUpProxyApi.md#get_har_log) | **GET** /har | 
[**healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck | 
[**reset_har_log**](BrowserUpProxyApi.md#reset_har_log) | **PUT** /har | 
[**set_har_page**](BrowserUpProxyApi.md#set_har_page) | **POST** /har/page | 
[**verify_not_present**](BrowserUpProxyApi.md#verify_not_present) | **POST** /verify/not_present/{name} | 
[**verify_present**](BrowserUpProxyApi.md#verify_present) | **POST** /verify/present/{name} | 
[**verify_size**](BrowserUpProxyApi.md#verify_size) | **POST** /verify/size/{size}/{name} | 
[**verify_sla**](BrowserUpProxyApi.md#verify_sla) | **POST** /verify/sla/{time}/{name} | 


# **add_custom_har_fields**
> add_custom_har_fields()



Add custom fields to the current HAR.

### Example

```python
import time
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)
    body = CustomHarData() # CustomHarData |  (optional)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        api_instance.add_custom_har_fields(body=body)
    except BrowserUpProxyClient.ApiException as e:
        print("Exception when calling BrowserUpProxyApi->add_custom_har_fields: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CustomHarData**](CustomHarData.md)|  | [optional]

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
**204** | The custom fields were added to the HAR. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_har_log**
> Har get_har_log()



Get the current HAR.

### Example

```python
import time
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from BrowserUpProxyClient.model.har import Har
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        api_response = api_instance.get_har_log()
        pprint(api_response)
    except BrowserUpProxyClient.ApiException as e:
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
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        api_instance.healthcheck()
    except BrowserUpProxyClient.ApiException as e:
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

# **reset_har_log**
> Har reset_har_log()



Starts a fresh HAR capture session.

### Example

```python
import time
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from BrowserUpProxyClient.model.har import Har
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        api_response = api_instance.reset_har_log()
        pprint(api_response)
    except BrowserUpProxyClient.ApiException as e:
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

# **set_har_page**
> Har set_har_page()



Starts a fresh HAR Page in the current active HAR

### Example

```python
import time
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from BrowserUpProxyClient.model.har import Har
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        api_response = api_instance.set_har_page()
        pprint(api_response)
    except BrowserUpProxyClient.ApiException as e:
        print("Exception when calling BrowserUpProxyApi->set_har_page: %s\n" % e)
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
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from BrowserUpProxyClient.model.verify_result import VerifyResult
from BrowserUpProxyClient.model.match_criteria import MatchCriteria
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)
    name = "HqXz" # str | The unique name for this verification operation
    match_criteria = MatchCriteria(
        url="url_example",
        page="page_example",
        status="status_example",
        content="content_example",
        content_type="content_type_example",
        websocket_message="websocket_message_example",
        request_header=,
        request_cookie=,
        response_header=,
        response_cookie=,
        json_valid=True,
        json_path="json_path_example",
        json_schema="json_schema_example",
    ) # MatchCriteria | Match criteria to select requests - response pairs for size tests

    # example passing only required values which don't have defaults set
    try:
        api_response = api_instance.verify_not_present(name, match_criteria)
        pprint(api_response)
    except BrowserUpProxyClient.ApiException as e:
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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **verify_present**
> VerifyResult verify_present(name, match_criteria)



Verify at least one matching item is present in the captured traffic

### Example

```python
import time
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from BrowserUpProxyClient.model.verify_result import VerifyResult
from BrowserUpProxyClient.model.match_criteria import MatchCriteria
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)
    name = "HqXz" # str | The unique name for this verification operation
    match_criteria = MatchCriteria(
        url="url_example",
        page="page_example",
        status="status_example",
        content="content_example",
        content_type="content_type_example",
        websocket_message="websocket_message_example",
        request_header=,
        request_cookie=,
        response_header=,
        response_cookie=,
        json_valid=True,
        json_path="json_path_example",
        json_schema="json_schema_example",
    ) # MatchCriteria | Match criteria to select requests - response pairs for size tests

    # example passing only required values which don't have defaults set
    try:
        api_response = api_instance.verify_present(name, match_criteria)
        pprint(api_response)
    except BrowserUpProxyClient.ApiException as e:
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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **verify_size**
> VerifyResult verify_size(size, name, match_criteria)



Verify matching items in the captured traffic meet the size criteria

### Example

```python
import time
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from BrowserUpProxyClient.model.verify_result import VerifyResult
from BrowserUpProxyClient.model.match_criteria import MatchCriteria
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)
    size = 0 # int | The size used for comparison, in kilobytes
    name = "HqXz" # str | The unique name for this verification operation
    match_criteria = MatchCriteria(
        url="url_example",
        page="page_example",
        status="status_example",
        content="content_example",
        content_type="content_type_example",
        websocket_message="websocket_message_example",
        request_header=,
        request_cookie=,
        response_header=,
        response_cookie=,
        json_valid=True,
        json_path="json_path_example",
        json_schema="json_schema_example",
    ) # MatchCriteria | Match criteria to select requests - response pairs for size tests

    # example passing only required values which don't have defaults set
    try:
        api_response = api_instance.verify_size(size, name, match_criteria)
        pprint(api_response)
    except BrowserUpProxyClient.ApiException as e:
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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **verify_sla**
> VerifyResult verify_sla(time, name, match_criteria)



Verify each traffic item matching the criteria meets is below SLA time

### Example

```python
import time
import BrowserUpProxyClient
from BrowserUpProxyClient.api import browser_up_proxy_api
from BrowserUpProxyClient.model.verify_result import VerifyResult
from BrowserUpProxyClient.model.match_criteria import MatchCriteria
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8088
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxyClient.Configuration(
    host = "http://localhost:8088"
)


# Enter a context with an instance of the API client
with BrowserUpProxyClient.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = browser_up_proxy_api.BrowserUpProxyApi(api_client)
    time = 0 # int | The time used for comparison
    name = "HqXz" # str | The unique name for this verification operation
    match_criteria = MatchCriteria(
        url="url_example",
        page="page_example",
        status="status_example",
        content="content_example",
        content_type="content_type_example",
        websocket_message="websocket_message_example",
        request_header=,
        request_cookie=,
        response_header=,
        response_cookie=,
        json_valid=True,
        json_path="json_path_example",
        json_schema="json_schema_example",
    ) # MatchCriteria | Match criteria to select requests - response pairs for size tests

    # example passing only required values which don't have defaults set
    try:
        api_response = api_instance.verify_sla(time, name, match_criteria)
        pprint(api_response)
    except BrowserUpProxyClient.ApiException as e:
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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

