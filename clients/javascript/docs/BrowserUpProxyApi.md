# BrowserUpProxyClient.BrowserUpProxyApi

All URIs are relative to *http://localhost:8088*

Method | HTTP request | Description
------------- | ------------- | -------------
[**addCustomHarFields**](BrowserUpProxyApi.md#addCustomHarFields) | **PUT** /har/page | 
[**getHarLog**](BrowserUpProxyApi.md#getHarLog) | **GET** /har | 
[**healthcheck**](BrowserUpProxyApi.md#healthcheck) | **GET** /healthcheck | 
[**resetHarLog**](BrowserUpProxyApi.md#resetHarLog) | **PUT** /har | 
[**setHarPage**](BrowserUpProxyApi.md#setHarPage) | **POST** /har/page | 
[**verifyNotPresent**](BrowserUpProxyApi.md#verifyNotPresent) | **POST** /verify/not_present/{name} | 
[**verifyPresent**](BrowserUpProxyApi.md#verifyPresent) | **POST** /verify/present/{name} | 
[**verifySLA**](BrowserUpProxyApi.md#verifySLA) | **POST** /verify/sla/{time}/{name} | 
[**verifySize**](BrowserUpProxyApi.md#verifySize) | **POST** /verify/size/{size}/{name} | 



## addCustomHarFields

> addCustomHarFields(opts)



Add custom fields to the current HAR.

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let opts = {
  'body': null // Object | 
};
apiInstance.addCustomHarFields(opts, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully.');
  }
});
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


## getHarLog

> Har getHarLog()



Get the current HAR.

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.getHarLog((error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
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


## healthcheck

> healthcheck()



Get the healthcheck

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.healthcheck((error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully.');
  }
});
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


## resetHarLog

> Har resetHarLog()



Starts a fresh HAR capture session.

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.resetHarLog((error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
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


## setHarPage

> Har setHarPage()



Starts a fresh HAR Page in the current active HAR

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.setHarPage((error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
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


## verifyNotPresent

> VerifyResult verifyNotPresent(name, matchCriteria)



Verify no matching items are present in the captured traffic

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let name = "name_example"; // String | The unique name for this verification operation
let matchCriteria = new BrowserUpProxyClient.MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
apiInstance.verifyNotPresent(name, matchCriteria, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **String**| The unique name for this verification operation | 
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verifyPresent

> VerifyResult verifyPresent(name, matchCriteria)



Verify at least one matching item is present in the captured traffic

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let name = "name_example"; // String | The unique name for this verification operation
let matchCriteria = new BrowserUpProxyClient.MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
apiInstance.verifyPresent(name, matchCriteria, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **String**| The unique name for this verification operation | 
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verifySLA

> VerifyResult verifySLA(time, name, matchCriteria)



Verify each traffic item matching the criteria meets is below SLA time

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let time = 56; // Number | The time used for comparison
let name = "name_example"; // String | The unique name for this verification operation
let matchCriteria = new BrowserUpProxyClient.MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
apiInstance.verifySLA(time, name, matchCriteria, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **time** | **Number**| The time used for comparison | 
 **name** | **String**| The unique name for this verification operation | 
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## verifySize

> VerifyResult verifySize(size, name, matchCriteria)



Verify matching items in the captured traffic meet the size criteria

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let size = 56; // Number | The size used for comparison, in kilobytes
let name = "name_example"; // String | The unique name for this verification operation
let matchCriteria = new BrowserUpProxyClient.MatchCriteria(); // MatchCriteria | Match criteria to select requests - response pairs for size tests
apiInstance.verifySize(size, name, matchCriteria, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **size** | **Number**| The size used for comparison, in kilobytes | 
 **name** | **String**| The unique name for this verification operation | 
 **matchCriteria** | [**MatchCriteria**](MatchCriteria.md)| Match criteria to select requests - response pairs for size tests | 

### Return type

[**VerifyResult**](VerifyResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

