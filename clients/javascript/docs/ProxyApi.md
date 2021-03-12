# BrowserUpProxyClient.ProxyApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**allowlistDelete**](ProxyApi.md#allowlistDelete) | **DELETE** /allowlist | 
[**allowlistGet**](ProxyApi.md#allowlistGet) | **GET** /allowlist | 
[**allowlistPost**](ProxyApi.md#allowlistPost) | **POST** /allowlist | 
[**blocklistGet**](ProxyApi.md#blocklistGet) | **GET** /blocklist | 
[**blocklistPost**](ProxyApi.md#blocklistPost) | **POST** /blocklist | 
[**harGet**](ProxyApi.md#harGet) | **GET** /har | 



## allowlistDelete

> allowlistDelete()



Deletes the AllowList, which will turn-off allowlist based filtering

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.ProxyApi();
apiInstance.allowlistDelete((error, data, response) => {
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


## allowlistGet

> AllowList allowlistGet()



Get an AllowList

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.ProxyApi();
apiInstance.allowlistGet((error, data, response) => {
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

[**AllowList**](AllowList.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## allowlistPost

> allowlistPost(opts)



Sets an AllowList

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.ProxyApi();
let opts = {
  'allowList': new BrowserUpProxyClient.AllowList() // AllowList | 
};
apiInstance.allowlistPost(opts, (error, data, response) => {
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
 **allowList** | [**AllowList**](AllowList.md)|  | [optional] 

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined


## blocklistGet

> BlockList blocklistGet()



Get a blocklist

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.ProxyApi();
apiInstance.blocklistGet((error, data, response) => {
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

[**BlockList**](BlockList.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## blocklistPost

> blocklistPost(opts)



Sets an BlockList

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.ProxyApi();
let opts = {
  'blockList': new BrowserUpProxyClient.BlockList() // BlockList | 
};
apiInstance.blocklistPost(opts, (error, data, response) => {
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
 **blockList** | [**BlockList**](BlockList.md)|  | [optional] 

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined


## harGet

> Har harGet()



Get the current HAR

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.ProxyApi();
apiInstance.harGet((error, data, response) => {
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

