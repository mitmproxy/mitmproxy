# BrowserUpProxyApi

All URIs are relative to *http://localhost:48088*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**addError**](BrowserUpProxyApi.md#addError) | **POST** /har/errors |  |
| [**addMetric**](BrowserUpProxyApi.md#addMetric) | **POST** /har/metrics |  |
| [**getHarLog**](BrowserUpProxyApi.md#getHarLog) | **GET** /har |  |
| [**healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck |  |
| [**newPage**](BrowserUpProxyApi.md#newPage) | **POST** /har/page |  |
| [**resetHarLog**](BrowserUpProxyApi.md#resetHarLog) | **PUT** /har |  |
| [**verifyNotPresent**](BrowserUpProxyApi.md#verifyNotPresent) | **POST** /verify/not_present/{name} |  |
| [**verifyPresent**](BrowserUpProxyApi.md#verifyPresent) | **POST** /verify/present/{name} |  |
| [**verifySLA**](BrowserUpProxyApi.md#verifySLA) | **POST** /verify/sla/{time}/{name} |  |
| [**verifySize**](BrowserUpProxyApi.md#verifySize) | **POST** /verify/size/{size}/{name} |  |


<a name="addError"></a>
# **addError**
> addError(error)



Add Custom Error to the captured traffic har

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
    defaultClient.setBasePath("http://localhost:48088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    Error error = new Error(); // Error | Receives an error to track. Internally, the error is stored in an array in the har under the _errors key
    try {
      apiInstance.addError(error);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#addError");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
```

### Parameters

| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **error** | [**Error**](Error.md)| Receives an error to track. Internally, the error is stored in an array in the har under the _errors key | |

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
| **204** | The Error was added. |  -  |
| **422** | The Error was invalid. |  -  |

<a name="addMetric"></a>
# **addMetric**
> addMetric(metric)



Add Custom Metric to the captured traffic har

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
    defaultClient.setBasePath("http://localhost:48088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    Metric metric = new Metric(); // Metric | Receives a new metric to add. The metric is stored, under the hood, in an array in the har under the _metrics key
    try {
      apiInstance.addMetric(metric);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#addMetric");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
```

### Parameters

| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **metric** | [**Metric**](Metric.md)| Receives a new metric to add. The metric is stored, under the hood, in an array in the har under the _metrics key | |

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
| **204** | The metric was added. |  -  |
| **422** | The metric was invalid. |  -  |

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
    defaultClient.setBasePath("http://localhost:48088");

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
| **200** | The current Har file. |  -  |

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
    defaultClient.setBasePath("http://localhost:48088");

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
| **200** | OK means all is well. |  -  |

<a name="newPage"></a>
# **newPage**
> Har newPage(title)



Starts a fresh HAR Page (Step) in the current active HAR to group requests.

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
    defaultClient.setBasePath("http://localhost:48088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    String title = "title_example"; // String | The unique title for this har page/step.
    try {
      Har result = apiInstance.newPage(title);
      System.out.println(result);
    } catch (ApiException e) {
      System.err.println("Exception when calling BrowserUpProxyApi#newPage");
      System.err.println("Status code: " + e.getCode());
      System.err.println("Reason: " + e.getResponseBody());
      System.err.println("Response headers: " + e.getResponseHeaders());
      e.printStackTrace();
    }
  }
}
```

### Parameters

| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **title** | **String**| The unique title for this har page/step. | |

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
| **200** | The current Har file. |  -  |

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
    defaultClient.setBasePath("http://localhost:48088");

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
| **200** | The current Har file. |  -  |

<a name="verifyNotPresent"></a>
# **verifyNotPresent**
> VerifyResult verifyNotPresent(name, matchCriteria)



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
    defaultClient.setBasePath("http://localhost:48088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    String name = "name_example"; // String | The unique name for this verification operation
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifyNotPresent(name, matchCriteria);
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

| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **name** | **String**| The unique name for this verification operation | |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

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
| **200** | The traffic had no matching items |  -  |
| **422** | The MatchCriteria are invalid. |  -  |

<a name="verifyPresent"></a>
# **verifyPresent**
> VerifyResult verifyPresent(name, matchCriteria)



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
    defaultClient.setBasePath("http://localhost:48088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    String name = "name_example"; // String | The unique name for this verification operation
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifyPresent(name, matchCriteria);
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

| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **name** | **String**| The unique name for this verification operation | |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

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
| **200** | The traffic conformed to the time criteria. |  -  |
| **422** | The MatchCriteria are invalid. |  -  |

<a name="verifySLA"></a>
# **verifySLA**
> VerifyResult verifySLA(time, name, matchCriteria)



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
    defaultClient.setBasePath("http://localhost:48088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    Integer time = 56; // Integer | The time used for comparison
    String name = "name_example"; // String | The unique name for this verification operation
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifySLA(time, name, matchCriteria);
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

| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **time** | **Integer**| The time used for comparison | |
| **name** | **String**| The unique name for this verification operation | |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

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
| **200** | The traffic conformed to the time criteria. |  -  |
| **422** | The MatchCriteria are invalid. |  -  |

<a name="verifySize"></a>
# **verifySize**
> VerifyResult verifySize(size, name, matchCriteria)



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
    defaultClient.setBasePath("http://localhost:48088");

    BrowserUpProxyApi apiInstance = new BrowserUpProxyApi(defaultClient);
    Integer size = 56; // Integer | The size used for comparison, in kilobytes
    String name = "name_example"; // String | The unique name for this verification operation
    MatchCriteria matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
    try {
      VerifyResult result = apiInstance.verifySize(size, name, matchCriteria);
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

| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **size** | **Integer**| The size used for comparison, in kilobytes | |
| **name** | **String**| The unique name for this verification operation | |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

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
| **200** | The traffic conformed to the size criteria. |  -  |
| **422** | The MatchCriteria are invalid. |  -  |

