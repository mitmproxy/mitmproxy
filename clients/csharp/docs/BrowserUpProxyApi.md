# BrowserUpMitmProxyClient.Api.BrowserUpProxyApi

All URIs are relative to *http://localhost:48088*

| Method | HTTP request | Description |
|--------|--------------|-------------|
| [**AddError**](BrowserUpProxyApi.md#adderror) | **POST** /har/errors |  |
| [**AddMetric**](BrowserUpProxyApi.md#addmetric) | **POST** /har/metrics |  |
| [**GetHarLog**](BrowserUpProxyApi.md#getharlog) | **GET** /har |  |
| [**Healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck |  |
| [**NewPage**](BrowserUpProxyApi.md#newpage) | **POST** /har/page |  |
| [**ResetHarLog**](BrowserUpProxyApi.md#resetharlog) | **PUT** /har |  |
| [**VerifyNotPresent**](BrowserUpProxyApi.md#verifynotpresent) | **POST** /verify/not_present/{name} |  |
| [**VerifyPresent**](BrowserUpProxyApi.md#verifypresent) | **POST** /verify/present/{name} |  |
| [**VerifySLA**](BrowserUpProxyApi.md#verifysla) | **POST** /verify/sla/{time}/{name} |  |
| [**VerifySize**](BrowserUpProxyApi.md#verifysize) | **POST** /verify/size/{size}/{name} |  |

<a name="adderror"></a>
# **AddError**
> void AddError (Error error)



Add Custom Error to the captured traffic har

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class AddErrorExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);
            var error = new Error(); // Error | Receives an error to track. Internally, the error is stored in an array in the har under the _errors key

            try
            {
                apiInstance.AddError(error);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.AddError: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the AddErrorWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    apiInstance.AddErrorWithHttpInfo(error);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.AddErrorWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
```

### Parameters

| Name | Type | Description | Notes |
|------|------|-------------|-------|
| **error** | [**Error**](Error.md) | Receives an error to track. Internally, the error is stored in an array in the har under the _errors key |  |

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
| **204** | The Error was added. |  -  |
| **422** | The Error was invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="addmetric"></a>
# **AddMetric**
> void AddMetric (Metric metric)



Add Custom Metric to the captured traffic har

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class AddMetricExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);
            var metric = new Metric(); // Metric | Receives a new metric to add. The metric is stored, under the hood, in an array in the har under the _metrics key

            try
            {
                apiInstance.AddMetric(metric);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.AddMetric: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the AddMetricWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    apiInstance.AddMetricWithHttpInfo(metric);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.AddMetricWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
```

### Parameters

| Name | Type | Description | Notes |
|------|------|-------------|-------|
| **metric** | [**Metric**](Metric.md) | Receives a new metric to add. The metric is stored, under the hood, in an array in the har under the _metrics key |  |

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
| **204** | The metric was added. |  -  |
| **422** | The metric was invalid. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="getharlog"></a>
# **GetHarLog**
> Har GetHarLog ()



Get the current HAR.

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class GetHarLogExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);

            try
            {
                Har result = apiInstance.GetHarLog();
                Debug.WriteLine(result);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.GetHarLog: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the GetHarLogWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    ApiResponse<Har> response = apiInstance.GetHarLogWithHttpInfo();
    Debug.Write("Status Code: " + response.StatusCode);
    Debug.Write("Response Headers: " + response.Headers);
    Debug.Write("Response Body: " + response.Data);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.GetHarLogWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="healthcheck"></a>
# **Healthcheck**
> void Healthcheck ()



Get the healthcheck

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class HealthcheckExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);

            try
            {
                apiInstance.Healthcheck();
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.Healthcheck: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the HealthcheckWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    apiInstance.HealthcheckWithHttpInfo();
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.HealthcheckWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
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
| **200** | OK means all is well. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="newpage"></a>
# **NewPage**
> Har NewPage (string title)



Starts a fresh HAR Page (Step) in the current active HAR to group requests.

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class NewPageExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);
            var title = "title_example";  // string | The unique title for this har page/step.

            try
            {
                Har result = apiInstance.NewPage(title);
                Debug.WriteLine(result);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.NewPage: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the NewPageWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    ApiResponse<Har> response = apiInstance.NewPageWithHttpInfo(title);
    Debug.Write("Status Code: " + response.StatusCode);
    Debug.Write("Response Headers: " + response.Headers);
    Debug.Write("Response Body: " + response.Data);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.NewPageWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
```

### Parameters

| Name | Type | Description | Notes |
|------|------|-------------|-------|
| **title** | **string** | The unique title for this har page/step. |  |

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="resetharlog"></a>
# **ResetHarLog**
> Har ResetHarLog ()



Starts a fresh HAR capture session.

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class ResetHarLogExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);

            try
            {
                Har result = apiInstance.ResetHarLog();
                Debug.WriteLine(result);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.ResetHarLog: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the ResetHarLogWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    ApiResponse<Har> response = apiInstance.ResetHarLogWithHttpInfo();
    Debug.Write("Status Code: " + response.StatusCode);
    Debug.Write("Response Headers: " + response.Headers);
    Debug.Write("Response Body: " + response.Data);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.ResetHarLogWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="verifynotpresent"></a>
# **VerifyNotPresent**
> VerifyResult VerifyNotPresent (string name, MatchCriteria matchCriteria)



Verify no matching items are present in the captured traffic

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class VerifyNotPresentExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);
            var name = "name_example";  // string | The unique name for this verification operation
            var matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests

            try
            {
                VerifyResult result = apiInstance.VerifyNotPresent(name, matchCriteria);
                Debug.WriteLine(result);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.VerifyNotPresent: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the VerifyNotPresentWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    ApiResponse<VerifyResult> response = apiInstance.VerifyNotPresentWithHttpInfo(name, matchCriteria);
    Debug.Write("Status Code: " + response.StatusCode);
    Debug.Write("Response Headers: " + response.Headers);
    Debug.Write("Response Body: " + response.Data);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.VerifyNotPresentWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
```

### Parameters

| Name | Type | Description | Notes |
|------|------|-------------|-------|
| **name** | **string** | The unique name for this verification operation |  |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="verifypresent"></a>
# **VerifyPresent**
> VerifyResult VerifyPresent (string name, MatchCriteria matchCriteria)



Verify at least one matching item is present in the captured traffic

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class VerifyPresentExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);
            var name = "name_example";  // string | The unique name for this verification operation
            var matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests

            try
            {
                VerifyResult result = apiInstance.VerifyPresent(name, matchCriteria);
                Debug.WriteLine(result);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.VerifyPresent: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the VerifyPresentWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    ApiResponse<VerifyResult> response = apiInstance.VerifyPresentWithHttpInfo(name, matchCriteria);
    Debug.Write("Status Code: " + response.StatusCode);
    Debug.Write("Response Headers: " + response.Headers);
    Debug.Write("Response Body: " + response.Data);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.VerifyPresentWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
```

### Parameters

| Name | Type | Description | Notes |
|------|------|-------------|-------|
| **name** | **string** | The unique name for this verification operation |  |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="verifysla"></a>
# **VerifySLA**
> VerifyResult VerifySLA (int time, string name, MatchCriteria matchCriteria)



Verify each traffic item matching the criteria meets is below SLA time

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class VerifySLAExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);
            var time = 56;  // int | The time used for comparison
            var name = "name_example";  // string | The unique name for this verification operation
            var matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests

            try
            {
                VerifyResult result = apiInstance.VerifySLA(time, name, matchCriteria);
                Debug.WriteLine(result);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.VerifySLA: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the VerifySLAWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    ApiResponse<VerifyResult> response = apiInstance.VerifySLAWithHttpInfo(time, name, matchCriteria);
    Debug.Write("Status Code: " + response.StatusCode);
    Debug.Write("Response Headers: " + response.Headers);
    Debug.Write("Response Body: " + response.Data);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.VerifySLAWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
```

### Parameters

| Name | Type | Description | Notes |
|------|------|-------------|-------|
| **time** | **int** | The time used for comparison |  |
| **name** | **string** | The unique name for this verification operation |  |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

<a name="verifysize"></a>
# **VerifySize**
> VerifyResult VerifySize (int size, string name, MatchCriteria matchCriteria)



Verify matching items in the captured traffic meet the size criteria

### Example
```csharp
using System.Collections.Generic;
using System.Diagnostics;
using BrowserUpMitmProxyClient.Api;
using BrowserUpMitmProxyClient.Client;
using BrowserUpMitmProxyClient.Model;

namespace Example
{
    public class VerifySizeExample
    {
        public static void Main()
        {
            Configuration config = new Configuration();
            config.BasePath = "http://localhost:48088";
            var apiInstance = new BrowserUpProxyApi(config);
            var size = 56;  // int | The size used for comparison, in kilobytes
            var name = "name_example";  // string | The unique name for this verification operation
            var matchCriteria = new MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests

            try
            {
                VerifyResult result = apiInstance.VerifySize(size, name, matchCriteria);
                Debug.WriteLine(result);
            }
            catch (ApiException  e)
            {
                Debug.Print("Exception when calling BrowserUpProxyApi.VerifySize: " + e.Message);
                Debug.Print("Status Code: " + e.ErrorCode);
                Debug.Print(e.StackTrace);
            }
        }
    }
}
```

#### Using the VerifySizeWithHttpInfo variant
This returns an ApiResponse object which contains the response data, status code and headers.

```csharp
try
{
    ApiResponse<VerifyResult> response = apiInstance.VerifySizeWithHttpInfo(size, name, matchCriteria);
    Debug.Write("Status Code: " + response.StatusCode);
    Debug.Write("Response Headers: " + response.Headers);
    Debug.Write("Response Body: " + response.Data);
}
catch (ApiException e)
{
    Debug.Print("Exception when calling BrowserUpProxyApi.VerifySizeWithHttpInfo: " + e.Message);
    Debug.Print("Status Code: " + e.ErrorCode);
    Debug.Print(e.StackTrace);
}
```

### Parameters

| Name | Type | Description | Notes |
|------|------|-------------|-------|
| **size** | **int** | The size used for comparison, in kilobytes |  |
| **name** | **string** | The unique name for this verification operation |  |
| **matchCriteria** | [**MatchCriteria**](MatchCriteria.md) | Match criteria to select requests - response pairs for size tests |  |

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

