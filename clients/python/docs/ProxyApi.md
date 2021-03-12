# BrowserUpProxy.ProxyApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**allowlist_delete**](ProxyApi.md#allowlist_delete) | **DELETE** /allowlist | 
[**allowlist_get**](ProxyApi.md#allowlist_get) | **GET** /allowlist | 
[**allowlist_post**](ProxyApi.md#allowlist_post) | **POST** /allowlist | 
[**blocklist_get**](ProxyApi.md#blocklist_get) | **GET** /blocklist | 
[**blocklist_post**](ProxyApi.md#blocklist_post) | **POST** /blocklist | 


# **allowlist_delete**
> allowlist_delete()



Deletes the AllowList, which will turn-off allowlist based filtering

### Example

```python
import time
import BrowserUpProxy
from BrowserUpProxy.api import proxy_api
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxy.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with BrowserUpProxy.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = proxy_api.ProxyApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        api_instance.allowlist_delete()
    except BrowserUpProxy.ApiException as e:
        print("Exception when calling ProxyApi->allowlist_delete: %s\n" % e)
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
**204** | The current allowlist, if any, was destroyed an all requests are enabled. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **allowlist_get**
> AllowList allowlist_get()



Get an AllowList

### Example

```python
import time
import BrowserUpProxy
from BrowserUpProxy.api import proxy_api
from BrowserUpProxy.model.allow_list import AllowList
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxy.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with BrowserUpProxy.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = proxy_api.ProxyApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        api_response = api_instance.allowlist_get()
        pprint(api_response)
    except BrowserUpProxy.ApiException as e:
        print("Exception when calling ProxyApi->allowlist_get: %s\n" % e)
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

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The current allowlist. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **allowlist_post**
> allowlist_post()



Sets an AllowList

### Example

```python
import time
import BrowserUpProxy
from BrowserUpProxy.api import proxy_api
from BrowserUpProxy.model.allow_list import AllowList
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxy.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with BrowserUpProxy.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = proxy_api.ProxyApi(api_client)
    allow_list = AllowList(
        status_code="status_code_example",
        url_pattern="url_pattern_example",
    ) # AllowList |  (optional)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        api_instance.allowlist_post(allow_list=allow_list)
    except BrowserUpProxy.ApiException as e:
        print("Exception when calling ProxyApi->allowlist_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **allow_list** | [**AllowList**](AllowList.md)|  | [optional]

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
**204** | Success! |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **blocklist_get**
> BlockList blocklist_get()



Get a blocklist

### Example

```python
import time
import BrowserUpProxy
from BrowserUpProxy.api import proxy_api
from BrowserUpProxy.model.block_list import BlockList
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxy.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with BrowserUpProxy.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = proxy_api.ProxyApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        api_response = api_instance.blocklist_get()
        pprint(api_response)
    except BrowserUpProxy.ApiException as e:
        print("Exception when calling ProxyApi->blocklist_get: %s\n" % e)
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

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The current blocklist. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **blocklist_post**
> blocklist_post()



Sets an BlockList

### Example

```python
import time
import BrowserUpProxy
from BrowserUpProxy.api import proxy_api
from BrowserUpProxy.model.block_list import BlockList
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = BrowserUpProxy.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with BrowserUpProxy.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = proxy_api.ProxyApi(api_client)
    block_list = BlockList(
        status_code="status_code_example",
        url_pattern="url_pattern_example",
        http_method_pattern="http_method_pattern_example",
    ) # BlockList |  (optional)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        api_instance.blocklist_post(block_list=block_list)
    except BrowserUpProxy.ApiException as e:
        print("Exception when calling ProxyApi->blocklist_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **block_list** | [**BlockList**](BlockList.md)|  | [optional]

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
**204** | Success! |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

