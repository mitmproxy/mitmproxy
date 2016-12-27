IVERSION = (1, 0, 1)
VERSION = ".".join(str(i) for i in IVERSION)
PATHOD = "pathod " + VERSION
MITMPROXY = "mitmproxy " + VERSION

if __name__ == "__main__":
    print(VERSION)
