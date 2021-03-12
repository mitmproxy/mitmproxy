# Build Instructions

 1. Copy `mitmproxy-$VERSION-py3-none-any.whl` into this directory.  
    You can get the latest public release at https://mitmproxy.org/downloads/.
 2. Replace $VERSION with your mitmproxy version and 
    run `docker build --build-arg MITMPROXY_WHEEL=mitmproxy-$VERSION-py3-none-any.whl .`.
