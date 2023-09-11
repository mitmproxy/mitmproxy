# HarEntryResponseContent


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**size** | **int** |  | 
**compression** | **int** |  | [optional] 
**mime_type** | **str** |  | 
**text** | **str** |  | [optional] 
**encoding** | **str** |  | [optional] 
**video_buffered_percent** | **int** |  | [optional] [default to -1]
**video_stall_count** | **int** |  | [optional] [default to -1]
**video_decoded_byte_count** | **int** |  | [optional] [default to -1]
**video_waiting_count** | **int** |  | [optional] [default to -1]
**video_error_count** | **int** |  | [optional] [default to -1]
**video_dropped_frames** | **int** |  | [optional] [default to -1]
**video_total_frames** | **int** |  | [optional] [default to -1]
**video_audio_bytes_decoded** | **int** |  | [optional] [default to -1]
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.har_entry_response_content import HarEntryResponseContent

# TODO update the JSON string below
json = "{}"
# create an instance of HarEntryResponseContent from a JSON string
har_entry_response_content_instance = HarEntryResponseContent.from_json(json)
# print the JSON string representation of the object
print HarEntryResponseContent.to_json()

# convert the object into a dict
har_entry_response_content_dict = har_entry_response_content_instance.to_dict()
# create an instance of HarEntryResponseContent from a dict
har_entry_response_content_form_dict = har_entry_response_content.from_dict(har_entry_response_content_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


