import secrets
from pathlib import Path

import objgraph

from mitmproxy import certs

if __name__ == "__main__":
    store = certs.CertStore.from_store(path=Path("~/.mitmproxy/").expanduser(), basename="mitmproxy", key_size=2048)
    store.STORE_CAP = 5

    for _ in range(5):
        store.get_cert(commonname=secrets.token_hex(16).encode(), sans=[], organization=None)

    objgraph.show_growth()

    for _ in range(20):
        store.get_cert(commonname=secrets.token_hex(16).encode(), sans=[], organization=None)

    print("====")
    objgraph.show_growth()
