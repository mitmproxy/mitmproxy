# NameValuePair


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name to match | [optional] 
**value** | **str** | Value to match | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.name_value_pair import NameValuePair

# TODO update the JSON string below
json = "{}"
# create an instance of NameValuePair from a JSON string
name_value_pair_instance = NameValuePair.from_json(json)
# print the JSON string representation of the object
print NameValuePair.to_json()

# convert the object into a dict
name_value_pair_dict = name_value_pair_instance.to_dict()
# create an instance of NameValuePair from a dict
name_value_pair_form_dict = name_value_pair.from_dict(name_value_pair_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


