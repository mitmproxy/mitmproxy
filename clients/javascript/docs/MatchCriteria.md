# BrowserUpProxyClient.MatchCriteria

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**url** | **String** | Request URL regexp to match | [optional] 
**page** | **String** | current|all | [optional] 
**status** | **String** | HTTP Status code to match. | [optional] 
**content** | **String** | Body content regexp content to match | [optional] 
**contentType** | **String** | Content type | [optional] 
**websocketMessage** | **String** | Websocket message text to match | [optional] 
**requestHeader** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**requestCookie** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**responseHeader** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**responseCookie** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**jsonValid** | **Boolean** | Is valid JSON | [optional] 
**jsonPath** | **String** | Has JSON path | [optional] 
**jsonSchema** | **String** | Validates against passed JSON schema | [optional] 


