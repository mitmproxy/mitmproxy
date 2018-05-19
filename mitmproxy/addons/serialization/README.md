### DumpWatcher

_still in development_

This addon measures and prints execution time of different available
serialization modules. At the current state, it compares 
dumps/loads time of Google Protocol Buffers and 
custom tnetstring implemented in mitmproxy.io;


### Example command
Run mitmproxy with the following args:

-p 8081 -s $PATH_TO_MITMPROXY\mitmproxy\mitmproxy\addons\serialization\dumpwatcher.py --set dumpwatcher=true --set store_dumps=true

Then, on cli:

wget -e use_proxy=yes -e http_proxy=127.0.0.1:8081 http://www.lolcats.com

### Roadmap
- Option to run dumps/loads multiple times and average for better
results

**Implementation in protobuf.py is still
experimental -- it just handles a dummy HTTPResponse object!**
