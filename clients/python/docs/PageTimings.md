# PageTimings


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**on_content_load** | **int** |  | [default to -1]
**on_load** | **int** |  | [default to -1]
**href** | **str** |  | [optional] [default to '']
**dns** | **int** |  | [optional] [default to -1]
**ssl** | **int** |  | [optional] [default to -1]
**time_to_first_byte** | **int** |  | [optional] [default to -1]
**cumulative_layout_shift** | **float** |  | [optional] [default to -1]
**largest_contentful_paint** | [**LargestContentfulPaint**](LargestContentfulPaint.md) |  | [optional] 
**first_paint** | **int** |  | [optional] [default to -1]
**first_input_delay** | **float** |  | [optional] [default to -1]
**dom_interactive** | **int** |  | [optional] [default to -1]
**first_contentful_paint** | **int** |  | [optional] [default to -1]
**comment** | **str** |  | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.page_timings import PageTimings

# TODO update the JSON string below
json = "{}"
# create an instance of PageTimings from a JSON string
page_timings_instance = PageTimings.from_json(json)
# print the JSON string representation of the object
print PageTimings.to_json()

# convert the object into a dict
page_timings_dict = page_timings_instance.to_dict()
# create an instance of PageTimings from a dict
page_timings_form_dict = page_timings.from_dict(page_timings_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


