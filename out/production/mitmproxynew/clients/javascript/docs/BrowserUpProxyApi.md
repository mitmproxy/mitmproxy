# BrowserUpProxyClient.BrowserUpProxyApi

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



## clearAdditionalHeaders

> clearAdditionalHeaders()



Clear the additional Headers

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.clearAdditionalHeaders((error, data, response) => {
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


## clearAllowList

> clearAllowList()



Clears the AllowList, which will turn-off allowlist based filtering

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.clearAllowList((error, data, response) => {
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


## clearBasicAuthSettings

> clearBasicAuthSettings(domain)



Clears Basic Auth for a domain, disabling Automatic Basic Auth for it.

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let domain = "domain_example"; // String | The domain for which to clear the basic auth settings
apiInstance.clearBasicAuthSettings(domain, (error, data, response) => {
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
 **domain** | **String**| The domain for which to clear the basic auth settings | 

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: Not defined


## getAdditionalHeaders

> Headers getAdditionalHeaders()



Get the current added Headers

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.getAdditionalHeaders((error, data, response) => {
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

[**Headers**](Headers.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## getAllowList

> AllowList getAllowList()



Get an AllowList

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.getAllowList((error, data, response) => {
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


## getBlockList

> BlockList getBlockList()



Get a blocklist

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.getBlockList((error, data, response) => {
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


## healthcheckGet

> healthcheckGet()



Get the healthcheck

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.healthcheckGet((error, data, response) => {
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


## setAdditionalHeaders

> Headers setAdditionalHeaders()



Set additional headers to add to requests

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
apiInstance.setAdditionalHeaders((error, data, response) => {
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

[**Headers**](Headers.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## setAllowList

> setAllowList(opts)



Sets an AllowList

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let opts = {
  'allowList': new BrowserUpProxyClient.AllowList() // AllowList | 
};
apiInstance.setAllowList(opts, (error, data, response) => {
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


## setBasicAuth

> setBasicAuth(domain, opts)



Enables automatic basic auth for a domain

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let domain = "domain_example"; // String | The domain for which this Basic Auth should be used
let opts = {
  'authBasic': new BrowserUpProxyClient.AuthBasic() // AuthBasic | 
};
apiInstance.setBasicAuth(domain, opts, (error, data, response) => {
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
 **domain** | **String**| The domain for which this Basic Auth should be used | 
 **authBasic** | [**AuthBasic**](AuthBasic.md)|  | [optional] 

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: Not defined


## setBlockList

> setBlockList(opts)



Sets an BlockList

### Example

```javascript
import BrowserUpProxyClient from 'browserup-proxy-client';

let apiInstance = new BrowserUpProxyClient.BrowserUpProxyApi();
let opts = {
  'blockList': new BrowserUpProxyClient.BlockList() // BlockList | 
};
apiInstance.setBlockList(opts, (error, data, response) => {
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

