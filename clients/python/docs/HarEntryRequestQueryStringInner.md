# HarEntryRequestQueryStringInner


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**value** | **str** |  | 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_request_query_string_inner import HarEntryRequestQueryStringInner

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryRequestQueryStringInner from a JSON string
har_entry_request_query_string_inner_instance = HarEntryRequestQueryStringInner.from_json(json)
# print the JSON string representation of the object
print HarEntryRequestQueryStringInner.to_json()

# convert the object into a dict
har_entry_request_query_string_inner_dict = har_entry_request_query_string_inner_instance.to_dict()
# create an instance of HarEntryRequestQueryStringInner from a dict
har_entry_request_query_string_inner_form_dict = har_entry_request_query_string_inner.from_dict(har_entry_request_query_string_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


