# HarEntryResponse


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **int** |  | 
**status_text** | **str** |  | 
**http_version** | **str** |  | 
**cookies** | [**List[HarEntryRequestCookiesInner]**](HarEntryRequestCookiesInner.md) |  | 
**headers** | [**List[Header]**](Header.md) |  | 
**content** | [**HarEntryResponseContent**](HarEntryResponseContent.md) |  | 
**redirect_url** | **str** |  | 
**headers_size** | **int** |  | 
**body_size** | **int** |  | 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_response import HarEntryResponse

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryResponse from a JSON string
har_entry_response_instance = HarEntryResponse.from_json(json)
# print the JSON string representation of the object
print HarEntryResponse.to_json()

# convert the object into a dict
har_entry_response_dict = har_entry_response_instance.to_dict()
# create an instance of HarEntryResponse from a dict
har_entry_response_form_dict = har_entry_response.from_dict(har_entry_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


