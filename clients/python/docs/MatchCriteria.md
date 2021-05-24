# MatchCriteria

A set of criteria for filtering HTTP Requests and Responses.                          Criteria are AND based, and use python regular expressions for string comparison

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**url** | **str** | Request URL regexp to match | [optional] 
**page** | **str** | current|all | [optional] 
**status** | **str** | HTTP Status code to match. | [optional] 
**content** | **str** | Body content regexp content to match | [optional] 
**content_type** | **str** | Content type | [optional] 
**websocket_message** | **str** | Websocket message text to match | [optional] 
**request_header** | **object** |  | [optional] 
**request_cookie** | **object** |  | [optional] 
**response_header** | **object** |  | [optional] 
**response_cookie** | **object** |  | [optional] 
**json_valid** | **bool** | Is valid JSON | [optional] 
**json_path** | **str** | Has JSON path | [optional] 
**json_schema** | **str** | Validates against passed JSON schema | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


