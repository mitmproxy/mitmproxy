# HarEntryRequest


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**method** | **str** |  | 
**url** | **str** |  | 
**http_version** | **str** |  | 
**cookies** | [**List[HarEntryRequestCookiesInner]**](HarEntryRequestCookiesInner.md) |  | 
**headers** | [**List[Header]**](Header.md) |  | 
**query_string** | [**List[HarEntryRequestQueryStringInner]**](HarEntryRequestQueryStringInner.md) |  | 
**post_data** | [**HarEntryRequestPostData**](HarEntryRequestPostData.md) |  | [optional] 
**headers_size** | **int** |  | 
**body_size** | **int** |  | 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_request import HarEntryRequest

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryRequest from a JSON string
har_entry_request_instance = HarEntryRequest.from_json(json)
# print the JSON string representation of the object
print HarEntryRequest.to_json()

# convert the object into a dict
har_entry_request_dict = har_entry_request_instance.to_dict()
# create an instance of HarEntryRequest from a dict
har_entry_request_form_dict = har_entry_request.from_dict(har_entry_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


