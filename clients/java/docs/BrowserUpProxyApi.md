# BrowserUpProxyApi

All URIs are relative to *http://localhost:8088*

Method | HTTP request | Description
------------- | ------------- | -------------
[**addCustomHarFields**](BrowserUpProxyApi.md#addCustomHarFields) | **PUT** /har/page | 
[**getHarLog**](BrowserUpProxyApi.md#getHarLog) | **GET** /har | 
[**healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck | 
[**resetHarLog**](BrowserUpProxyApi.md#resetHarLog) | **PUT** /har | 
[**setHarPage**](BrowserUpProxyApi.md#setHarPage) | **POST** /har/page | 
[**verifyNotPresent**](BrowserUpProxyApi.md#verifyNotPresent) | **POST** /verify/not_present | 
[**verifyPresent**](BrowserUpProxyApi.md#verifyPresent) | **POST** /verify/present | 
[**verifySLA**](BrowserUpProxyApi.md#verifySLA) | **POST** /verify/sla/{time} | 
[**verifySize**](BrowserUpProxyApi.md#verifySize) | **POST** /verify/size/{size} | 


<a name="addCustomHarFields"></a>
# **addCustomHarFields**
> addCustomHarFields(body)



Add custom fields to the current HAR.

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
    defaultClient.setBasePath("http://localhost:8088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    Object body = null; // Object | 
    try {
      apiInstance.addCustomHarFields(body);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#addCustomHarFields");
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
 **body** | **Object**|  | [optional]

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
**204** | The custom fields were added to the HAR. |  -  |

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
    defaultClient.setBasePath("http://localhost:8088");

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

<a name="healthcheck"></a>
# **healthcheck**
> healthcheck()



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
    defaultClient.setBasePath("http://localhost:8088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    try {
      apiInstance.healthcheck();
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#healthcheck");
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
    defaultClient.setBasePath("http://localhost:8088");

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
    defaultClient.setBasePath("http://localhost:8088");

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

<a name="verifyNotPresent"></a>
# **verifyNotPresent**
> VerifyResult verifyNotPresent(matchCriteria)



Verify no matching items are present in the captured traffic

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
    defaultClient.setBasePath("http://localhost:8088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifyNotPresent(matchCriteria);
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#verifyNotPresent");
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
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests |

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

<a name="verifyPresent"></a>
# **verifyPresent**
> VerifyResult verifyPresent(matchCriteria)



Verify at least one matching item is present in the captured traffic

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
    defaultClient.setBasePath("http://localhost:8088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifyPresent(matchCriteria);
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#verifyPresent");
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
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests |

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

<a name="verifySLA"></a>
# **verifySLA**
> VerifyResult verifySLA(time, matchCriteria)



Verify each traffic item matching the criteria meets is below SLA time

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
    defaultClient.setBasePath("http://localhost:8088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    Integer time = 56; // Integer | The time used for comparison
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifySLA(time, matchCriteria);
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#verifySLA");
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
 **time** | **Integer**| The time used for comparison |
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests |

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

<a name="verifySize"></a>
# **verifySize**
> VerifyResult verifySize(size, matchCriteria)



Verify matching items in the captured traffic meet the size criteria

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
    defaultClient.setBasePath("http://localhost:8088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    Integer size = 56; // Integer | The size used for comparison
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifySize(size, matchCriteria);
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#verifySize");
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
 **size** | **Integer**| The size used for comparison |
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests |

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

