IVERSION = (2, 0, 0)
VERSION = ".".join(str(i) for i in IVERSION)
PATHOD = "pathod " + VERSION
MITMPROXY = "mitmproxy " + VERSION

if __name__ == "__main__":  # pragma: no cover
    print(VERSION)
