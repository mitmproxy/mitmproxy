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
> addError(Error)



    Add Custom Error to the captured traffic har

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **Error** | [**Error**](../Models/Error.md)| Receives an error to track. Internally, the error is stored in an array in the har under the _errors key | |

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined

<a name="addMetric"></a>
# **addMetric**
> addMetric(Metric)



    Add Custom Metric to the captured traffic har

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **Metric** | [**Metric**](../Models/Metric.md)| Receives a new metric to add. The metric is stored, under the hood, in an array in the har under the _metrics key | |

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined

<a name="getHarLog"></a>
# **getHarLog**
> Har getHarLog()



    Get the current HAR.

### Parameters
This endpoint does not need any parameter.

### Return type

[**Har**](../Models/Har.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

<a name="healthcheck"></a>
# **healthcheck**
> healthcheck()



    Get the healthcheck

### Parameters
This endpoint does not need any parameter.

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: Not defined

<a name="newPage"></a>
# **newPage**
> Har newPage(title)



    Starts a fresh HAR Page (Step) in the current active HAR to group requests.

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **title** | **String**| The unique title for this har page/step. | [default to null] |

### Return type

[**Har**](../Models/Har.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

<a name="resetHarLog"></a>
# **resetHarLog**
> Har resetHarLog()



    Starts a fresh HAR capture session.

### Parameters
This endpoint does not need any parameter.

### Return type

[**Har**](../Models/Har.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

<a name="verifyNotPresent"></a>
# **verifyNotPresent**
> VerifyResult verifyNotPresent(name, MatchCriteria)



    Verify no matching items are present in the captured traffic

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **name** | **String**| The unique name for this verification operation | [default to null] |
| **MatchCriteria** | [**MatchCriteria**](../Models/MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

### Return type

[**VerifyResult**](../Models/VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

<a name="verifyPresent"></a>
# **verifyPresent**
> VerifyResult verifyPresent(name, MatchCriteria)



    Verify at least one matching item is present in the captured traffic

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **name** | **String**| The unique name for this verification operation | [default to null] |
| **MatchCriteria** | [**MatchCriteria**](../Models/MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

### Return type

[**VerifyResult**](../Models/VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

<a name="verifySLA"></a>
# **verifySLA**
> VerifyResult verifySLA(time, name, MatchCriteria)



    Verify each traffic item matching the criteria meets is below SLA time

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **time** | **Integer**| The time used for comparison | [default to null] |
| **name** | **String**| The unique name for this verification operation | [default to null] |
| **MatchCriteria** | [**MatchCriteria**](../Models/MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

### Return type

[**VerifyResult**](../Models/VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

<a name="verifySize"></a>
# **verifySize**
> VerifyResult verifySize(size, name, MatchCriteria)



    Verify matching items in the captured traffic meet the size criteria

### Parameters

|Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **size** | **Integer**| The size used for comparison, in kilobytes | [default to null] |
| **name** | **String**| The unique name for this verification operation | [default to null] |
| **MatchCriteria** | [**MatchCriteria**](../Models/MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | |

### Return type

[**VerifyResult**](../Models/VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

