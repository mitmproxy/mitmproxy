# Action


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**id** | **str** |  | [optional] 
**class_name** | **str** |  | [optional] 
**tag_name** | **str** |  | [optional] 
**xpath** | **str** |  | [optional] 
**data_attributes** | **str** |  | [optional] 
**form_name** | **str** |  | [optional] 
**content** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.action import Action

# TODO update the JSON string below
json = "{}"
# create an instance of Action from a JSON string
action_instance = Action.from_json(json)
# print the JSON string representation of the object
print Action.to_json()

# convert the object into a dict
action_dict = action_instance.to_dict()
# create an instance of Action from a dict
action_form_dict = action.from_dict(action_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


