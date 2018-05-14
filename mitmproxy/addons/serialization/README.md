### DumpWatcher

_still in development_

This addon measures and prints execution time of different available
serialization modules. At the current state, it compares 
dumps/loads time of Google Protocol Buffers and 
custom tnetstring implemented in mitmproxy.io;

### Roadmap

- Option to run dumps/loads multiple times and average for better
results
- Option to save the blobs to SQLite DB and measure write/read
 time

**Implementation in protobuf.py is still
experimental -- it just handles a dummy HTTPResponse object!**
