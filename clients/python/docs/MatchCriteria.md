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
**request_header** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**request_cookie** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**response_header** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**response_cookie** | [**NameValuePair**](NameValuePair.md) |  | [optional] 
**json_valid** | **bool** | Is valid JSON | [optional] 
**json_path** | **str** | Has JSON path | [optional] 
**json_schema** | **str** | Validates against passed JSON schema | [optional] 
**error_if_no_traffic** | **bool** | If the proxy has NO traffic at all, return error | [optional] [default to True]

## Example

```python
from BrowserUpMitmProxyClient.models.match_criteria import MatchCriteria

# TODO update the JSON string below
json = "{}"
# create an instance of MatchCriteria from a JSON string
match_criteria_instance = MatchCriteria.from_json(json)
# print the JSON string representation of the object
print MatchCriteria.to_json()

# convert the object into a dict
match_criteria_dict = match_criteria_instance.to_dict()
# create an instance of MatchCriteria from a dict
match_criteria_form_dict = match_criteria.from_dict(match_criteria_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


