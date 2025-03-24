This is a fork of the mitmproxy project by a company named browserup. The mitmproxy 
is used to man-in-the-middle connections to provide debugging info, allow for security research
and other uses.

Browserup uses the mitmproxy to capture traffic from within containers that are run during a load test.
This captured traffic, through mitmproxy addons, is used to build a HAR (HTTP Archive) file. The HAR
file is made available via an API.  The API is also used to control the proxy, and to add custom metrics
to a har at runtime, as well as adding verifications for HAR content. Clients for 
this API are generated in multiple languages via the open api specification.  The clients live in /clients
which should be ignored, as they are generated files.

Browserup extends mitmproxy's mitmdump executable with addons 
The most important code for browserup live in mmitmproxy/addons/browserup