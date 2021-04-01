"""
Make events hooks non-blocking.

When event hooks are decorated with @concurrent, they will be run in their own thread, freeing the main event loop.
Please note that this generally opens the door to race conditions and decreases performance if not required.
"""
import time

from mitmproxy.script import concurrent


@concurrent  # Remove this and see what happens
def request(flow):
    # This is ugly in mitmproxy's UI, but you don't want to use mitmproxy.ctx.log from a different thread.
    print(f"handle request: {flow.request.host}{flow.request.path}")
    time.sleep(5)
    print(f"start  request: {flow.request.host}{flow.request.path}")
