# Har


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**log** | [**HarLog**](HarLog.md) |  | 

## Example

```python
from BrowserUpMitmProxyClient.models.har import Har

# TODO update the JSON string below
json = "{}"
# create an instance of Har from a JSON string
har_instance = Har.from_json(json)
# print the JSON string representation of the object
print Har.to_json()

# convert the object into a dict
har_dict = har_instance.to_dict()
# create an instance of Har from a dict
har_form_dict = har.from_dict(har_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


