# BrowserUpMitmProxyClient.Model.MatchCriteria
A set of criteria for filtering HTTP Requests and Responses.                          Criteria are AND based, and use python regular expressions for string comparison

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Url** | **string** | Request URL regexp to match | [optional] 
**Page** | **string** | current|all | [optional] 
**Status** | **string** | HTTP Status code to match. | [optional] 
**Content** | **string** | Body content regexp content to match | [optional] 
**ContentType** | **string** | Content type | [optional] 
**WebsocketMessage** | **string** | Websocket message text to match | [optional] 
**RequestHeader** | [**MatchCriteriaRequestHeader**](MatchCriteriaRequestHeader.md) |  | [optional] 
**RequestCookie** | [**MatchCriteriaRequestHeader**](MatchCriteriaRequestHeader.md) |  | [optional] 
**ResponseHeader** | [**MatchCriteriaRequestHeader**](MatchCriteriaRequestHeader.md) |  | [optional] 
**ResponseCookie** | [**MatchCriteriaRequestHeader**](MatchCriteriaRequestHeader.md) |  | [optional] 
**JsonValid** | **bool** | Is valid JSON | [optional] 
**JsonPath** | **string** | Has JSON path | [optional] 
**JsonSchema** | **string** | Validates against passed JSON schema | [optional] 
**ErrorIfNoTraffic** | **bool** | If the proxy has NO traffic at all, return error | [optional] [default to true]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

