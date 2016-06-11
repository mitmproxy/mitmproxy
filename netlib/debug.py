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
    if d[0]:
        data.append("Linux distro: %s %s %s"%d)

    d = platform.mac_ver()
    if d[0]:
        data.append("Mac version: %s %s %s"%d)

    d = platform.win32_ver()
    if d[0]:
        data.append("Windows version: %s %s %s %s"%d)

    return "\n".join(data)
