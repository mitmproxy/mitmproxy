---
title: "Blocking Websites and Requests"
menu:
concepts:
weight: 1
---

Mitmproxy's Blocklist feature provides a simple method for controlling the proxy's response to certain requests.
There are various scenarios where this functionality is useful.

:filter:BlockCommand:http_status_code
Arguments:

### Filter
A [Filter](./concepts-filters.md) 

## Block Commands

#### BLOCK

Block all traffic that ***matches*** the filter.

Example: 

`:~t image:BLOCK:200`

This command blocks all requests with "image" in their content type and returns an empty response with status 200.

#### BLOCK_UNLESS

BLOCK_UNLESS is the less forgiving cousin of BLOCK. It
blocks all traffic that does ***not* match** the filter.

This command blocks all traffic except to the mysite.com domain. It returns 404 for traffic to all other domains.

Avoid polluting your analytics
:BLOCK: ~t javascript & ~d (hs-scripts|segment\.com|yandex.ru|google-analytics|mxpnl|woopra|adobedtm|amplitude||hotjar|heapanalytics):200


#### STATUS Codes

Any [HTTP Status Code ](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)

##### I want to block requests entirely, and not respond! 

Good news! HTTP Status code 444, although unofficial, means "connection closed with"




* Avoid overwhelming 3rd party websites and components that would usually be loaded by a page
 
* Avoid polluting analytics data with automated traffic
* Block ad networks or other traffic. If it is an ad network used by your own website, displaying ads to bots ruins your pricing/quality scores
* Quickly block image loads block_list: [:~d browserup.com & ~u png:200] so save bandwidth, etc.
* Quickly stub an ajax request to avoid a 404 that triggers a JS error callback

The AllowList has two modes of operation.

For all usual HTTP status codes, when a request matches, an empty response with the desired HTTP Status is be returned.

mitmproxy honors the unofficial 444 HTTP status code Nginx uses to represent 
"close the connection without providing *any* response or response code." 
In short, if response code 444 is specified, no response will occur for matching items. 

