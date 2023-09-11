# HarLogCreator


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**version** | **str** |  | 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_log_creator import HarLogCreator

# TODO update the JSON string below
json = "{}"
# create an instance of HarLogCreator from a JSON string
har_log_creator_instance = HarLogCreator.from_json(json)
# print the JSON string representation of the object
print HarLogCreator.to_json()

# convert the object into a dict
har_log_creator_dict = har_log_creator_instance.to_dict()
# create an instance of HarLogCreator from a dict
har_log_creator_form_dict = har_log_creator.from_dict(har_log_creator_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


