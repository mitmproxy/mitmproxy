from __future__ import (absolute_import, print_function, division)

import os
import sys
import threading
import signal
import platform
import traceback

from netlib import version

from OpenSSL import SSL


def sysinfo():
    data = [
        "Mitmproxy version: %s" % version.VERSION,
        "Python version: %s" % platform.python_version(),
        "Platform: %s" % platform.platform(),
        "SSL version: %s" % SSL.SSLeay_version(SSL.SSLEAY_VERSION).decode(),
    ]
    d = platform.linux_distribution()
    t = "Linux distro: %s %s %s" % d
    if d[0]:  # pragma: no-cover
        data.append(t)

    d = platform.mac_ver()
    t = "Mac version: %s %s %s" % d
    if d[0]:  # pragma: no-cover
        data.append(t)

    d = platform.win32_ver()
    t = "Windows version: %s %s %s %s" % d
    if d[0]:  # pragma: no-cover
        data.append(t)

    return "\n".join(data)


def dump_info(signal=None, frame=None, file=sys.stdout):  # pragma: no cover
    print("****************************************************", file=file)
    print("Summary", file=file)
    print("=======", file=file)

    try:
        import psutil
    except:
        print("(psutil not installed, skipping some debug info)", file=file)
    else:
        p = psutil.Process()
        print("num threads: ", p.num_threads(), file=file)
        if hasattr(p, "num_fds"):
            print("num fds: ", p.num_fds(), file=file)
        print("memory: ", p.memory_info(), file=file)

        print(file=file)
        print("Files", file=file)
        print("=====", file=file)
        for i in p.open_files():
            print(i, file=file)

        print(file=file)
        print("Connections", file=file)
        print("===========", file=file)
        for i in p.connections():
            print(i, file=file)

    print(file=file)
    print("Threads", file=file)
    print("=======", file=file)
    bthreads = []
    for i in threading.enumerate():
        if hasattr(i, "_threadinfo"):
            bthreads.append(i)
        else:
            print(i.name, file=file)
    bthreads.sort(key=lambda x: x._thread_started)
    for i in bthreads:
        print(i._threadinfo(), file=file)

    print("****************************************************", file=file)


def dump_stacks(signal=None, frame=None, file=sys.stdout):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append(
            "\n# Thread: %s(%d)" % (
                id2name.get(threadId, ""), threadId
            )
        )
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    print("\n".join(code), file=file)


def register_info_dumpers():
    if os.name != "nt":
        signal.signal(signal.SIGUSR1, dump_info)
        signal.signal(signal.SIGUSR2, dump_stacks)
