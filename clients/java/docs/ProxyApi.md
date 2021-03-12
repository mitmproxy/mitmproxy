# ProxyApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**allowlistDelete**](ProxyApi.md#allowlistDelete) | **DELETE** /allowlist | 
[**allowlistGet**](ProxyApi.md#allowlistGet) | **GET** /allowlist | 
[**allowlistPost**](ProxyApi.md#allowlistPost) | **POST** /allowlist | 
[**blocklistGet**](ProxyApi.md#blocklistGet) | **GET** /blocklist | 
[**blocklistPost**](ProxyApi.md#blocklistPost) | **POST** /blocklist | 


<a name="allowlistDelete"></a>
# **allowlistDelete**
> allowlistDelete()



Deletes the AllowList, which will turn-off allowlist based filtering

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.ProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost");

    ProxyApi apiInstance = new ProxyApi(defaultClient);
    try {
      apiInstance.allowlistDelete();
    } catch (ApiException e) {
      System.err.println("Exception when calling ProxyApi#allowlistDelete");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | The current allowlist, if any, was destroyed an all requests are enabled. |  -  |

<a name="allowlistGet"></a>
# **allowlistGet**
> AllowList allowlistGet()



Get an AllowList

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.ProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost");

    ProxyApi apiInstance = new ProxyApi(defaultClient);
    try {
      AllowList result = apiInstance.allowlistGet();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling ProxyApi#allowlistGet");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
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

<a name="allowlistPost"></a>
# **allowlistPost**
> allowlistPost(allowList)



Sets an AllowList

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.ProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost");

    ProxyApi apiInstance = new ProxyApi(defaultClient);
    AllowList allowList = new AllowList(); // AllowList | 
    try {
      apiInstance.allowlistPost(allowList);
    } catch (ApiException e) {
      System.err.println("Exception when calling ProxyApi#allowlistPost");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **allowList** | [**AllowList**](AllowList.md)|  | [optional]

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: Not defined

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Success! |  -  |

<a name="blocklistGet"></a>
# **blocklistGet**
> BlockList blocklistGet()



Get a blocklist

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.ProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost");

    ProxyApi apiInstance = new ProxyApi(defaultClient);
    try {
      BlockList result = apiInstance.blocklistGet();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling ProxyApi#blocklistGet");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
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

<a name="blocklistPost"></a>
# **blocklistPost**
> blocklistPost(blockList)



Sets an BlockList

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.ProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost");

    ProxyApi apiInstance = new ProxyApi(defaultClient);
    BlockList blockList = new BlockList(); // BlockList | 
    try {
      apiInstance.blocklistPost(blockList);
    } catch (ApiException e) {
      System.err.println("Exception when calling ProxyApi#blocklistPost");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **blockList** | [**BlockList**](BlockList.md)|  | [optional]

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: Not defined

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Success! |  -  |

