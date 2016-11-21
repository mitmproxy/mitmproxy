# Mitmproxy Scripting API

Mitmproxy has a powerful scripting API that allows you to control almost any aspect of traffic being 
proxied. In fact, much of mitmproxy’s own core functionality is implemented using the exact same API 
exposed to scripters (see [mitmproxy/addons](../mitmproxy/addons)).

This directory contains some examples of the scripting API. We recommend to start with the
ones in [simple/](./simple).

|  :warning: | If you are browsing this on GitHub, make sure to select the git tag matching your mitmproxy version. |
|------------|------------------------------------------------------------------------------------------------------|


Some inline scripts may require additional dependencies, which can be installed using
`pip install mitmproxy[examples]`.