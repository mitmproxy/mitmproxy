# BrowserupMitmProxy::HarEntryResponseContent

## Properties

| Name | Type | Description | Notes |
| ---- | ---- | ----------- | ----- |
| **size** | **Integer** |  |  |
| **compression** | **Integer** |  | [optional] |
| **mime_type** | **String** |  |  |
| **text** | **String** |  | [optional] |
| **encoding** | **String** |  | [optional] |
| **_video_buffered_percent** | **Integer** |  | [optional][default to -1] |
| **_video_stall_count** | **Integer** |  | [optional][default to -1] |
| **_video_decoded_byte_count** | **Integer** |  | [optional][default to -1] |
| **_video_waiting_count** | **Integer** |  | [optional][default to -1] |
| **_video_error_count** | **Integer** |  | [optional][default to -1] |
| **_video_dropped_frames** | **Integer** |  | [optional][default to -1] |
| **_video_total_frames** | **Integer** |  | [optional][default to -1] |
| **_video_audio_bytes_decoded** | **Integer** |  | [optional][default to -1] |
| **comment** | **String** |  | [optional] |

## Example

```ruby
require 'browserup_mitmproxy_client'

instance = BrowserupMitmProxy::HarEntryResponseContent.new(
  size: null,
  compression: null,
  mime_type: null,
  text: null,
  encoding: null,
  _video_buffered_percent: null,
  _video_stall_count: null,
  _video_decoded_byte_count: null,
  _video_waiting_count: null,
  _video_error_count: null,
  _video_dropped_frames: null,
  _video_total_frames: null,
  _video_audio_bytes_decoded: null,
  comment: null
)
```

