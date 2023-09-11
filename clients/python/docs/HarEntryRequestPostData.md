# HarEntryRequestPostData

Posted data info.

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**mime_type** | **str** |  | 
**text** | **str** |  | [optional] 
**params** | [**List[HarEntryRequestPostDataParamsInner]**](HarEntryRequestPostDataParamsInner.md) |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_request_post_data import HarEntryRequestPostData

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryRequestPostData from a JSON string
har_entry_request_post_data_instance = HarEntryRequestPostData.from_json(json)
# print the JSON string representation of the object
print HarEntryRequestPostData.to_json()

# convert the object into a dict
har_entry_request_post_data_dict = har_entry_request_post_data_instance.to_dict()
# create an instance of HarEntryRequestPostData from a dict
har_entry_request_post_data_form_dict = har_entry_request_post_data.from_dict(har_entry_request_post_data_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


