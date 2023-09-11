# HarEntryRequestCookiesInner


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**value** | **str** |  | 
**path** | **str** |  | [optional] 
**domain** | **str** |  | [optional] 
**expires** | **str** |  | [optional] 
**http_only** | **bool** |  | [optional] 
**secure** | **bool** |  | [optional] 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_request_cookies_inner import HarEntryRequestCookiesInner

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryRequestCookiesInner from a JSON string
har_entry_request_cookies_inner_instance = HarEntryRequestCookiesInner.from_json(json)
# print the JSON string representation of the object
print HarEntryRequestCookiesInner.to_json()

# convert the object into a dict
har_entry_request_cookies_inner_dict = har_entry_request_cookies_inner_instance.to_dict()
# create an instance of HarEntryRequestCookiesInner from a dict
har_entry_request_cookies_inner_form_dict = har_entry_request_cookies_inner.from_dict(har_entry_request_cookies_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


