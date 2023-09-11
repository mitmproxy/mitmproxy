# HarEntryCacheBeforeRequest


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**expires** | **str** |  | [optional] 
**last_access** | **str** |  | 
**e_tag** | **str** |  | 
**hit_count** | **int** |  | 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_cache_before_request import HarEntryCacheBeforeRequest

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryCacheBeforeRequest from a JSON string
har_entry_cache_before_request_instance = HarEntryCacheBeforeRequest.from_json(json)
# print the JSON string representation of the object
print HarEntryCacheBeforeRequest.to_json()

# convert the object into a dict
har_entry_cache_before_request_dict = har_entry_cache_before_request_instance.to_dict()
# create an instance of HarEntryCacheBeforeRequest from a dict
har_entry_cache_before_request_form_dict = har_entry_cache_before_request.from_dict(har_entry_cache_before_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


