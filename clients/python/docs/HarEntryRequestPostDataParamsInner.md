# HarEntryRequestPostDataParamsInner


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**value** | **str** |  | [optional] 
**file_name** | **str** |  | [optional] 
**content_type** | **str** |  | [optional] 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_request_post_data_params_inner import HarEntryRequestPostDataParamsInner

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryRequestPostDataParamsInner from a JSON string
har_entry_request_post_data_params_inner_instance = HarEntryRequestPostDataParamsInner.from_json(json)
# print the JSON string representation of the object
print HarEntryRequestPostDataParamsInner.to_json()

# convert the object into a dict
har_entry_request_post_data_params_inner_dict = har_entry_request_post_data_params_inner_instance.to_dict()
# create an instance of HarEntryRequestPostDataParamsInner from a dict
har_entry_request_post_data_params_inner_form_dict = har_entry_request_post_data_params_inner.from_dict(har_entry_request_post_data_params_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


