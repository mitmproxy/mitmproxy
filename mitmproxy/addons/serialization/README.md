### Serialization Proposal

_still in development_

#### Dumpwatcher
It measures and prints execution time of different available
serialization modules. At the current state, it compares 
dumps/loads time of Google Protocol Buffers and 
custom tnetstring implemented in mitmproxy.io;

#### Streamtester
It puts the current implementation under stress, streaming 
a single flow with a given period. This serves as a throughput
measure to tweak async modules and find the right strategy.


### Example command
Run mitmproxy with the following args:

-p 8081 -s $PATH_TO_MITMPROXY\mitmproxy\mitmproxy\addons\serialization\dumpwatcher.py --set dumpwatcher=true --set store_dumps=true

Then, on cli:

wget -e use_proxy=yes -e http_proxy=127.0.0.1:8081 http://www.lolcats.com

**Implementation in protobuf.py is still
experimental -- it just handles a dummy HTTPResponse object!**
