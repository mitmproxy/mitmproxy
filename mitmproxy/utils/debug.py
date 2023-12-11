import asyncio
import gc
import linecache
import os
import platform
import signal
import sys
import threading
import traceback
from collections import Counter
from contextlib import redirect_stdout

from OpenSSL import SSL

from mitmproxy import version
from mitmproxy.utils import asyncio_utils


def dump_system_info():
    mitmproxy_version = version.get_dev_version()
    openssl_version: str | bytes = SSL.SSLeay_version(SSL.SSLEAY_VERSION)
    if isinstance(openssl_version, bytes):
        openssl_version = openssl_version.decode()

    data = [
        f"Mitmproxy: {mitmproxy_version}",
        f"Python:    {platform.python_version()}",
        f"OpenSSL:   {openssl_version}",
        f"Platform:  {platform.platform()}",
    ]
    return "\n".join(data)


def dump_info(signal=None, frame=None, file=sys.stdout):  # pragma: no cover
    with redirect_stdout(file):
        print("****************************************************")
        print("Summary")
        print("=======")

        try:
            import psutil
        except ModuleNotFoundError:
            print("(psutil not installed, skipping some debug info)")
        else:
            p = psutil.Process()
            print("num threads: ", p.num_threads())
            if hasattr(p, "num_fds"):
                print("num fds: ", p.num_fds())
            print("memory: ", p.memory_info())

            print()
            print("Files")
            print("=====")
            for i in p.open_files():
                print(i)

            print()
            print("Connections")
            print("===========")
            for i in p.connections():
                print(i)

        print()
        print("Threads")
        print("=======")
        bthreads = []
        for i in threading.enumerate():
            if hasattr(i, "_threadinfo"):
                bthreads.append(i)
            else:
                print(i.name)
        bthreads.sort(key=lambda x: x._thread_started)
        for i in bthreads:
            print(i._threadinfo())

        print()
        print("Memory")
        print("======")
        gc.collect()
        objs = Counter(str(type(i)) for i in gc.get_objects())

        for cls, count in objs.most_common(20):
            print(f"{count} {cls}")

        print()
        print("Memory (mitmproxy only)")
        print("=======================")
        mitm_objs = Counter({k: v for k, v in objs.items() if "mitmproxy" in k})
        for cls, count in mitm_objs.most_common(20):
            print(f"{count} {cls}")

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            print()
            print("Tasks")
            print("=======")
            for task in asyncio.all_tasks():
                f = task.get_stack(limit=1)[0]
                line = linecache.getline(
                    f.f_code.co_filename, f.f_lineno, f.f_globals
                ).strip()
                line = f"{line}  # at {os.path.basename(f.f_code.co_filename)}:{f.f_lineno}"
                print(f"{asyncio_utils.task_repr(task)}\n" f"    {line}")

        print("****************************************************")

    if os.getenv("MITMPROXY_DEBUG_EXIT"):  # pragma: no cover
        sys.exit(1)


def dump_stacks(signal=None, frame=None, file=sys.stdout):
    id2name = {th.ident: th.name for th in threading.enumerate()}
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId, ""), threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    print("\n".join(code), file=file)
    if os.getenv("MITMPROXY_DEBUG_EXIT"):  # pragma: no cover
        sys.exit(1)


def register_info_dumpers():
    if os.name != "nt":  # pragma: windows no cover
        signal.signal(signal.SIGUSR1, dump_info)
        signal.signal(signal.SIGUSR2, dump_stacks)
