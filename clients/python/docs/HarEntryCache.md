# HarEntryCache


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**before_request** | [**HarEntryCacheBeforeRequest**](HarEntryCacheBeforeRequest.md) |  | [optional] 
**after_request** | [**HarEntryCacheBeforeRequest**](HarEntryCacheBeforeRequest.md) |  | [optional] 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_cache import HarEntryCache

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryCache from a JSON string
har_entry_cache_instance = HarEntryCache.from_json(json)
# print the JSON string representation of the object
print HarEntryCache.to_json()

# convert the object into a dict
har_entry_cache_dict = har_entry_cache_instance.to_dict()
# create an instance of HarEntryCache from a dict
har_entry_cache_form_dict = har_entry_cache.from_dict(har_entry_cache_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


