"""
This module provides a @concurrent decorator primitive to
offload computations from mitmproxy's main master thread.
"""

import asyncio
import inspect

from mitmproxy import hooks


def concurrent(fn):
    if fn.__name__ not in set(hooks.all_hooks.keys()) - {"load", "configure"}:
        raise NotImplementedError(
            "Concurrent decorator not supported for '%s' method." % fn.__name__
        )

    async def _concurrent(*args):
        def run():
            if inspect.iscoroutinefunction(fn):
                # Run the async function in a new event loop
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(fn(*args))
                finally:
                    loop.close()
            else:
                fn(*args)

        await asyncio.get_running_loop().run_in_executor(None, run)

    return _concurrent
