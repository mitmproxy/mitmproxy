import asyncio
import sys

if sys.platform == 'win32':
    # workaround for
    # https://github.com/tornadoweb/tornado/issues/2751
    # https://www.tornadoweb.org/en/stable/index.html#installation
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
