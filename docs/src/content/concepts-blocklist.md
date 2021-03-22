---
title: "Blocking Websites and Requests"
menu:
concepts:
weight: 7
---
# Blocklist

Blocklists provide a method for controlling mitmproxy's response to certain requests by specifying an 
array of block commands.

Use-cases:

* Block specific API calls (3rd party or otherwise) that would usually be loaded by a webpage
* Block analytics calls to avoid polluting analytics data with automated traffic
* Block ad networks or other traffic. Automated traffic harms your clickthrough/quality scores for ads on your website.
* Make your own ad-blocker
* Block image loads to save bandwidth, etc.
* Stub an Ajax request to avoid a 404 that triggers a JS error callback
* Limit all calls to a staging environment with *allow-only*

## Block Command

###### Arguments:

```
[:filter:block-type:status]
```

* `filter` (**mandatory**): An mitmproxy [Filter](./concepts-filters.md) to select traffic.
* `block-type` (**mandatory**): The type of block. One of either "block" or the opposite exclusionary "allow-only"
* `status`  (**mandatory**) HTTP Status code. Status code 444 is special cased to "hang up."

### Block Type

#### block

Block all traffic that ***matches*** the filter.

Examples: 

* Stop images from downloading by blocking the image content type
```
:~t image:block:200`
```
* Stop analytics calls by blocking javascript content loads from 3rd party analytics domains 
```
:~t javascript & ~d (hs-scripts|segment|yandex|google-analytics|mxpnl|woopra|adobedtm|amplitude||hotjar|heapanalytics):block:200
```

This command blocks all requests with "image" in their content type and returns an empty response with status 200.

#### allow-only

allow-only stops any traffic that ***does not*** match the filter.

This command blocks all traffic except to the mysite.com domain. It returns 404 for traffic to all other domains.

Examples:

Limit an app to only access URLs on your staging environment. If it tries to connect anywhere else, it
gets an empty 200 response.

```
:~d mysite.com & ~u staging:allow-only:200
```


### Status

The [HTTP Status Code ](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) to respond-with.


##### Can I make mitmproxy just not respond at all?

Yes! HTTP Status code **444** means "indicate that the server has returned no information to the 
client and closed the connection." Mitmproxy honors this behavior. In short, if response 444 is specified, no response 
will occur at all.
