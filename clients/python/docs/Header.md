# Header


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**value** | **str** |  | 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.header import Header

# TODO update the JSON string below
json = "{}"
# create an instance of Header from a JSON string
header_instance = Header.from_json(json)
# print the JSON string representation of the object
print Header.to_json()

# convert the object into a dict
header_dict = header_instance.to_dict()
# create an instance of Header from a dict
header_form_dict = header.from_dict(header_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


