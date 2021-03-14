# BrowserUpProxyApi

All URIs are relative to *http://localhost:8080*

Method | HTTP request | Description
------------- | ------------- | -------------
[**clearAdditionalHeaders**](BrowserUpProxyApi.md#clearAdditionalHeaders) | **DELETE** /additional_headers | 
[**clearAllowList**](BrowserUpProxyApi.md#clearAllowList) | **DELETE** /allowlist | 
[**clearBasicAuthSettings**](BrowserUpProxyApi.md#clearBasicAuthSettings) | **DELETE** /auth_basic/{domain} | 
[**getAdditionalHeaders**](BrowserUpProxyApi.md#getAdditionalHeaders) | **GET** /additional_headers | 
[**getAllowList**](BrowserUpProxyApi.md#getAllowList) | **GET** /allowlist | 
[**getBlockList**](BrowserUpProxyApi.md#getBlockList) | **GET** /blocklist | 
[**getHarLog**](BrowserUpProxyApi.md#getHarLog) | **GET** /har | 
[**healthcheckGet**](BrowserUpProxyApi.md#healthcheckGet) | **GET** /healthcheck | 
[**resetHarLog**](BrowserUpProxyApi.md#resetHarLog) | **PUT** /har | 
[**setAdditionalHeaders**](BrowserUpProxyApi.md#setAdditionalHeaders) | **POST** /additional_headers | 
[**setAllowList**](BrowserUpProxyApi.md#setAllowList) | **POST** /allowlist | 
[**setBasicAuth**](BrowserUpProxyApi.md#setBasicAuth) | **POST** /auth_basic/{domain} | 
[**setBlockList**](BrowserUpProxyApi.md#setBlockList) | **POST** /blocklist | 
[**setHarPage**](BrowserUpProxyApi.md#setHarPage) | **PUT** /har/page | 


<a name="clearAdditionalHeaders"></a>
# **clearAdditionalHeaders**
> clearAdditionalHeaders()



Clear the additional Headers

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      apiInstance.clearAdditionalHeaders();
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#clearAdditionalHeaders");
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
**204** | The current additional header settings were cleared. |  -  |

<a name="clearAllowList"></a>
# **clearAllowList**
> clearAllowList()



Clears the AllowList, which will turn-off allowlist based filtering

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      apiInstance.clearAllowList();
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#clearAllowList");
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
**204** | The allowlist was cleared and allowlist-based filtering is OFF until a new list is posted. |  -  |

<a name="clearBasicAuthSettings"></a>
# **clearBasicAuthSettings**
> clearBasicAuthSettings(domain)



Clears Basic Auth for a domain, disabling Automatic Basic Auth for it.

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    String domain = "domain_example"; // String | The domain for which to clear the basic auth settings
    try {
      apiInstance.clearBasicAuthSettings(domain);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#clearBasicAuthSettings");
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
 **domain** | **String**| The domain for which to clear the basic auth settings |

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
**204** | The current Basic Authorization setting is cleared and no longer used for requests to a domain. |  -  |

<a name="getAdditionalHeaders"></a>
# **getAdditionalHeaders**
> Headers getAdditionalHeaders()



Get the current added Headers

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      Headers result = apiInstance.getAdditionalHeaders();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#getAdditionalHeaders");
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

[**Headers**](Headers.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | The current header settings. |  -  |

<a name="getAllowList"></a>
# **getAllowList**
> AllowList getAllowList()



Get an AllowList

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      AllowList result = apiInstance.getAllowList();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#getAllowList");
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
**200** | The current allowlist. Only allowed requests will pass through. |  -  |

<a name="getBlockList"></a>
# **getBlockList**
> BlockList getBlockList()



Get a blocklist

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      BlockList result = apiInstance.getBlockList();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#getBlockList");
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

<a name="getHarLog"></a>
# **getHarLog**
> Har getHarLog()



Get the current HAR.

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      Har result = apiInstance.getHarLog();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#getHarLog");
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

<a name="healthcheckGet"></a>
# **healthcheckGet**
> healthcheckGet()



Get the healthcheck

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      apiInstance.healthcheckGet();
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#healthcheckGet");
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
**200** | OK means all is well. |  -  |

<a name="resetHarLog"></a>
# **resetHarLog**
> Har resetHarLog()



Starts a fresh HAR capture session.

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      Har result = apiInstance.resetHarLog();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#resetHarLog");
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

<a name="setAdditionalHeaders"></a>
# **setAdditionalHeaders**
> Headers setAdditionalHeaders()



Set additional headers to add to requests

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      Headers result = apiInstance.setAdditionalHeaders();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#setAdditionalHeaders");
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

[**Headers**](Headers.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Show the current additional header settings. |  -  |

<a name="setAllowList"></a>
# **setAllowList**
> setAllowList(allowList)



Sets an AllowList

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    AllowList allowList = new AllowList(); // AllowList | 
    try {
      apiInstance.setAllowList(allowList);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#setAllowList");
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

<a name="setBasicAuth"></a>
# **setBasicAuth**
> setBasicAuth(domain, authBasic)



Enables automatic basic auth for a domain

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    String domain = "domain_example"; // String | The domain for which this Basic Auth should be used
    AuthBasic authBasic = new AuthBasic(); // AuthBasic | 
    try {
      apiInstance.setBasicAuth(domain, authBasic);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#setBasicAuth");
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
 **domain** | **String**| The domain for which this Basic Auth should be used |
 **authBasic** | [**AuthBasic**](AuthBasic.md)|  | [optional]

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

<a name="setBlockList"></a>
# **setBlockList**
> setBlockList(blockList)



Sets an BlockList

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    BlockList blockList = new BlockList(); // BlockList | 
    try {
      apiInstance.setBlockList(blockList);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#setBlockList");
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

<a name="setHarPage"></a>
# **setHarPage**
> Har setHarPage()



Starts a fresh HAR Page in the current active HAR

### Example
```java
// Import classes:
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Configuration;
import com.browserup.proxy_client.models.*;
import com.browserup.proxy.api.BrowserUpProxyApi;

public class Example {
  public static void main(String[] args) {
    ApiClient defaultClient = Configuration.getDefaultApiClient();
    defaultClient.setBasePath("http://localhost:8080");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      Har result = apiInstance.setHarPage();
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#setHarPage");
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

