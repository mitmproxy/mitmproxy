# HarEntryTimings


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**dns** | **int** |  | [default to -1]
**connect** | **int** |  | [default to -1]
**blocked** | **int** |  | [default to -1]
**send** | **int** |  | [default to -1]
**wait** | **int** |  | [default to -1]
**receive** | **int** |  | [default to -1]
**ssl** | **int** |  | [default to -1]
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_timings import HarEntryTimings

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryTimings from a JSON string
har_entry_timings_instance = HarEntryTimings.from_json(json)
# print the JSON string representation of the object
print HarEntryTimings.to_json()

# convert the object into a dict
har_entry_timings_dict = har_entry_timings_instance.to_dict()
# create an instance of HarEntryTimings from a dict
har_entry_timings_form_dict = har_entry_timings.from_dict(har_entry_timings_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


