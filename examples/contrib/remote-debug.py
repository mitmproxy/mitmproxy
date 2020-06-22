"""
This script enables remote debugging of the mitmproxy console *UI* with PyCharm.
For general debugging purposes, it is easier to just debug mitmdump within PyCharm.

Usage:
    - pip install pydevd on the mitmproxy machine
    - Open the Run/Debug Configuration dialog box in PyCharm, and select the
      Python Remote Debug configuration type.
    - Debugging works in the way that mitmproxy connects to the debug server
      on startup. Specify host and port that mitmproxy can use to reach your
      PyCharm instance on startup.
    - Adjust this inline script accordingly.
    - Start debug server in PyCharm
    - Set breakpoints
    - Start mitmproxy -s remote_debug.py
"""


def load(l):
    import pydevd_pycharm
    pydevd_pycharm.settrace("localhost", port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)
