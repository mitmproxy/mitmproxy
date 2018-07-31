import os
import subprocess
import sys

VERSION = "4.0.4"
PATHOD = "pathod " + VERSION
MITMPROXY = "mitmproxy " + VERSION

# Serialization format version. This is displayed nowhere, it just needs to be incremented by one
# for each change in the file format.
FLOW_FORMAT_VERSION = 7


def get_dev_version() -> str:
    """
    Return a detailed version string, sourced either from VERSION or obtained dynamically using git.
    """

    mitmproxy_version = VERSION

    here = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    try:
        git_describe = subprocess.check_output(
            ['git', 'describe', '--long'],
            stderr=subprocess.STDOUT,
            cwd=here,
        )
        last_tag, tag_dist, commit = git_describe.decode().strip().rsplit("-", 2)
        commit = commit.lstrip("g")[:7]
        tag_dist = int(tag_dist)
    except Exception:
        pass
    else:
        # Add commit info for non-tagged releases
        if tag_dist > 0:
            mitmproxy_version += f" (+{tag_dist}, commit {commit})"

    # PyInstaller build indicator, if using precompiled binary
    if getattr(sys, 'frozen', False):
        mitmproxy_version += " binary"

    return mitmproxy_version


if __name__ == "__main__":  # pragma: no cover
    print(VERSION)
