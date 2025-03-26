# Documentation for BrowserUp MitmProxy

<a name="documentation-for-api-endpoints"></a>
## Documentation for API Endpoints

All URIs are relative to *http://localhost:48088*

| Class | Method | HTTP request | Description |
|------------ | ------------- | ------------- | -------------|
| *BrowserUpProxyApi* | [**addError**](Apis/BrowserUpProxyApi.md#adderror) | **POST** /har/errors | Add Custom Error to the captured traffic har |
*BrowserUpProxyApi* | [**addMetric**](Apis/BrowserUpProxyApi.md#addmetric) | **POST** /har/metrics | Add Custom Metric to the captured traffic har |
*BrowserUpProxyApi* | [**getHarLog**](Apis/BrowserUpProxyApi.md#getharlog) | **GET** /har | Get the current HAR. |
*BrowserUpProxyApi* | [**healthcheck**](Apis/BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck | Get the healthcheck |
*BrowserUpProxyApi* | [**newPage**](Apis/BrowserUpProxyApi.md#newpage) | **POST** /har/page | Starts a fresh HAR Page (Step) in the current active HAR to group requests. |
*BrowserUpProxyApi* | [**resetHarLog**](Apis/BrowserUpProxyApi.md#resetharlog) | **PUT** /har | Starts a fresh HAR capture session. |
*BrowserUpProxyApi* | [**verifyNotPresent**](Apis/BrowserUpProxyApi.md#verifynotpresent) | **POST** /verify/not_present/{name} | Verify no matching items are present in the captured traffic |
*BrowserUpProxyApi* | [**verifyPresent**](Apis/BrowserUpProxyApi.md#verifypresent) | **POST** /verify/present/{name} | Verify at least one matching item is present in the captured traffic |
*BrowserUpProxyApi* | [**verifySLA**](Apis/BrowserUpProxyApi.md#verifysla) | **POST** /verify/sla/{time}/{name} | Verify each traffic item matching the criteria meets is below SLA time |
*BrowserUpProxyApi* | [**verifySize**](Apis/BrowserUpProxyApi.md#verifysize) | **POST** /verify/size/{size}/{name} | Verify matching items in the captured traffic meet the size criteria |


<a name="documentation-for-models"></a>
## Documentation for Models

 - [Action](./Models/Action.md)
 - [Error](./Models/Error.md)
 - [Har](./Models/Har.md)
 - [HarEntry](./Models/HarEntry.md)
 - [HarEntry_cache](./Models/HarEntry_cache.md)
 - [HarEntry_cache_beforeRequest](./Models/HarEntry_cache_beforeRequest.md)
 - [HarEntry_cache_beforeRequest_oneOf](./Models/HarEntry_cache_beforeRequest_oneOf.md)
 - [HarEntry_request](./Models/HarEntry_request.md)
 - [HarEntry_request_cookies_inner](./Models/HarEntry_request_cookies_inner.md)
 - [HarEntry_request_postData](./Models/HarEntry_request_postData.md)
 - [HarEntry_request_postData_params_inner](./Models/HarEntry_request_postData_params_inner.md)
 - [HarEntry_request_queryString_inner](./Models/HarEntry_request_queryString_inner.md)
 - [HarEntry_response](./Models/HarEntry_response.md)
 - [HarEntry_response_content](./Models/HarEntry_response_content.md)
 - [HarEntry_timings](./Models/HarEntry_timings.md)
 - [Har_log](./Models/Har_log.md)
 - [Har_log_creator](./Models/Har_log_creator.md)
 - [Header](./Models/Header.md)
 - [LargestContentfulPaint](./Models/LargestContentfulPaint.md)
 - [MatchCriteria](./Models/MatchCriteria.md)
 - [MatchCriteria_request_header](./Models/MatchCriteria_request_header.md)
 - [Metric](./Models/Metric.md)
 - [NameValuePair](./Models/NameValuePair.md)
 - [Page](./Models/Page.md)
 - [PageTiming](./Models/PageTiming.md)
 - [PageTimings](./Models/PageTimings.md)
 - [VerifyResult](./Models/VerifyResult.md)
 - [WebSocketMessage](./Models/WebSocketMessage.md)


<a name="documentation-for-authorization"></a>
## Documentation for Authorization

All endpoints do not require authorization.
