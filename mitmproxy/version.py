IVERSION = (3, 0, 0)
VERSION = ".".join(str(i) for i in IVERSION)
PATHOD = "pathod " + VERSION
MITMPROXY = "mitmproxy " + VERSION

# Serialization format version. This is displayed nowhere, it just needs to be incremented by one
# for each change the the file format.
FLOW_FORMAT_VERSION = 4

if __name__ == "__main__":
    print(VERSION)
