# MatchCriteria
## Properties

| Name | Type | Description | Notes |
|------------ | ------------- | ------------- | -------------|
| **url** | **String** | Request URL regexp to match | [optional] [default to null] |
| **page** | **String** | current|all | [optional] [default to null] |
| **status** | **String** | HTTP Status code to match. | [optional] [default to null] |
| **content** | **String** | Body content regexp content to match | [optional] [default to null] |
| **content\_type** | **String** | Content type | [optional] [default to null] |
| **websocket\_message** | **String** | Websocket message text to match | [optional] [default to null] |
| **request\_header** | [**MatchCriteria_request_header**](MatchCriteria_request_header.md) |  | [optional] [default to null] |
| **request\_cookie** | [**MatchCriteria_request_header**](MatchCriteria_request_header.md) |  | [optional] [default to null] |
| **response\_header** | [**MatchCriteria_request_header**](MatchCriteria_request_header.md) |  | [optional] [default to null] |
| **response\_cookie** | [**MatchCriteria_request_header**](MatchCriteria_request_header.md) |  | [optional] [default to null] |
| **json\_valid** | **Boolean** | Is valid JSON | [optional] [default to null] |
| **json\_path** | **String** | Has JSON path | [optional] [default to null] |
| **json\_schema** | **String** | Validates against passed JSON schema | [optional] [default to null] |
| **error\_if\_no\_traffic** | **Boolean** | If the proxy has NO traffic at all, return error | [optional] [default to true] |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

