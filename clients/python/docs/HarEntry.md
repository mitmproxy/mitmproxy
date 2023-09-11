# HarEntry


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**pageref** | **str** |  | [optional] 
**started_date_time** | **datetime** |  | 
**time** | **int** |  | 
**request** | [**HarEntryRequest**](HarEntryRequest.md) |  | 
**response** | [**HarEntryResponse**](HarEntryResponse.md) |  | 
**cache** | [**HarEntryCache**](HarEntryCache.md) |  | 
**timings** | [**HarEntryTimings**](HarEntryTimings.md) |  | 
**server_ip_address** | **str** |  | [optional] 
**web_socket_messages** | [**List[WebSocketMessage]**](WebSocketMessage.md) |  | [optional] 
**connection** | **str** |  | [optional] 
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry import HarEntry

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntry from a JSON string
har_entry_instance = HarEntry.from_json(json)
# print the JSON string representation of the object
print HarEntry.to_json()

# convert the object into a dict
har_entry_dict = har_entry_instance.to_dict()
# create an instance of HarEntry from a dict
har_entry_form_dict = har_entry.from_dict(har_entry_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


