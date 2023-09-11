# Page


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**started_date_time** | **datetime** |  | 
**id** | **str** |  | 
**title** | **str** |  | 
**verifications** | [**List[VerifyResult]**](VerifyResult.md) |  | [optional] [default to []]
**counters** | [**List[Counter]**](Counter.md) |  | [optional] [default to []]
**errors** | [**List[Error]**](Error.md) |  | [optional] [default to []]
**page_timings** | [**PageTimings**](PageTimings.md) |  | 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.page import Page

# TODO update the JSON string below
json = "{}"
# create an instance of Page from a JSON string
page_instance = Page.from_json(json)
# print the JSON string representation of the object
print Page.to_json()

# convert the object into a dict
page_dict = page_instance.to_dict()
# create an instance of Page from a dict
page_form_dict = page.from_dict(page_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


