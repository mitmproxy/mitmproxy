# PageTiming


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**on_content_load** | **float** | onContentLoad per the browser | [optional] 
**on_load** | **float** | onLoad per the browser | [optional] 
**first_input_delay** | **float** | firstInputDelay from the browser | [optional] 
**first_paint** | **float** | firstPaint from the browser | [optional] 
**cumulative_layout_shift** | **float** | cumulativeLayoutShift metric from the browser | [optional] 
**largest_contentful_paint** | **float** | largestContentfulPaint from the browser | [optional] 
**dom_interactive** | **float** | domInteractive from the browser | [optional] 
**first_contentful_paint** | **float** | firstContentfulPaint from the browser | [optional] 
**dns** | **float** | dns lookup time from the browser | [optional] 
**ssl** | **float** | Ssl connect time from the browser | [optional] 
**time_to_first_byte** | **float** | Time to first byte of the page&#39;s first request per the browser | [optional] 
**href** | **str** | Top level href, including hashtag, etc per the browser | [optional] 

## Example

```python
from BrowserUpMitmProxyClient.models.page_timing import PageTiming

# TODO update the JSON string below
json = "{}"
# create an instance of PageTiming from a JSON string
page_timing_instance = PageTiming.from_json(json)
# print the JSON string representation of the object
print PageTiming.to_json()

# convert the object into a dict
page_timing_dict = page_timing_instance.to_dict()
# create an instance of PageTiming from a dict
page_timing_form_dict = page_timing.from_dict(page_timing_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


