# VerifyResult


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**result** | **bool** | Result True / False | [optional] 
**name** | **str** | Name | [optional] 
**type** | **str** | Type | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.verify_result import VerifyResult

# TODO update the JSON string below
json = "{}"
# create an instance of VerifyResult from a JSON string
verify_result_instance = VerifyResult.from_json(json)
# print the JSON string representation of the object
print VerifyResult.to_json()

# convert the object into a dict
verify_result_dict = verify_result_instance.to_dict()
# create an instance of VerifyResult from a dict
verify_result_form_dict = verify_result.from_dict(verify_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


