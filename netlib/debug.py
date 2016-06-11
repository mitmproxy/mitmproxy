from __future__ import (absolute_import, print_function, division)

import sys
import threading
import signal
import platform

import psutil

from netlib import version


def sysinfo():
    data = [
        "Mitmproxy version: %s" % version.VERSION,
        "Python version: %s" % platform.python_version(),
        "Platform: %s" % platform.platform(),
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


def dump_info(sig, frm, file=sys.stdout):  # pragma: no cover
    p = psutil.Process()

    print("****************************************************", file=file)
    print("Summary", file=file)
    print("=======", file=file)
    print("num threads: ", p.num_threads(), file=file)
    print("num fds: ", p.num_fds(), file=file)
    print("memory: ", p.memory_info(), file=file)

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

    print("****************************************************", file=file)


def register_info_dumper():  # pragma: no cover
    signal.signal(signal.SIGUSR1, dump_info)
