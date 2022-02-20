"""
Make events hooks non-blocking using async or @concurrent
"""
import asyncio
import time

from mitmproxy.script import concurrent
from mitmproxy import ctx


# Hooks can be async, which allows the hook to call async functions and perform async I/O
# without blocking other requests. This is generally preferred for new addons.
async def request(flow):
    ctx.log.info(f"handle request: {flow.request.host}{flow.request.path}")
    await asyncio.sleep(5)
    ctx.log.info(f"start  request: {flow.request.host}{flow.request.path}")


# Another option is to use @concurrent, which launches the hook in its own thread.
# Please note that this generally opens the door to race conditions and decreases performance if not required.
# Rename the function below to request(flow) to try it out.
@concurrent  # Remove this to make it synchronous and see what happens
def request_concurrent(flow):
    # This is ugly in mitmproxy's UI, but you don't want to use mitmproxy.ctx.log from a different thread.
    print(f"handle request: {flow.request.host}{flow.request.path}")
    time.sleep(5)
    print(f"start  request: {flow.request.host}{flow.request.path}")
