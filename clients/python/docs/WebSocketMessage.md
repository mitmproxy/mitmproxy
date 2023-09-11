# WebSocketMessage


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | 
**opcode** | **float** |  | 
**data** | **str** |  | 
**time** | **float** |  | 

## Example

```python
from BrowserUpMitmProxyClient.models.web_socket_message import WebSocketMessage

# TODO update the JSON string below
json = "{}"
# create an instance of WebSocketMessage from a JSON string
web_socket_message_instance = WebSocketMessage.from_json(json)
# print the JSON string representation of the object
print WebSocketMessage.to_json()

# convert the object into a dict
web_socket_message_dict = web_socket_message_instance.to_dict()
# create an instance of WebSocketMessage from a dict
web_socket_message_form_dict = web_socket_message.from_dict(web_socket_message_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


