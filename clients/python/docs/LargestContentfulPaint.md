# LargestContentfulPaint


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**start_time** | **int** |  | [optional] [default to -1]
**size** | **int** |  | [optional] [default to -1]
**dom_path** | **str** |  | [optional] [default to '']
**tag** | **str** |  | [optional] [default to '']

## Example

```python
from BrowserUpMitmProxyClient.models.largest_contentful_paint import LargestContentfulPaint

# TODO update the JSON string below
json = "{}"
# create an instance of LargestContentfulPaint from a JSON string
largest_contentful_paint_instance = LargestContentfulPaint.from_json(json)
# print the JSON string representation of the object
print LargestContentfulPaint.to_json()

# convert the object into a dict
largest_contentful_paint_dict = largest_contentful_paint_instance.to_dict()
# create an instance of LargestContentfulPaint from a dict
largest_contentful_paint_form_dict = largest_contentful_paint.from_dict(largest_contentful_paint_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


