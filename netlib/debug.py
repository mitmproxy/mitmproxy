import platform
from netlib import version

"""
    Some utilities to help with debugging.
"""

def sysinfo():
    data = [
        "Mitmproxy verison: %s"%version.VERSION,
        "Python version: %s"%platform.python_version(),
        "Platform: %s"%platform.platform(),
    ]
    d = platform.linux_distribution()
    t = "Linux distro: %s %s %s"%d
    if d[0]: # pragma: no-cover
        data.append(t)

    d = platform.mac_ver()
    t = "Mac version: %s %s %s"%d
    if d[0]: # pragma: no-cover
        data.append(t)

    d = platform.win32_ver()
    t = "Windows version: %s %s %s %s"%d
    if d[0]: # pragma: no-cover
        data.append(t)

    return "\n".join(data)
