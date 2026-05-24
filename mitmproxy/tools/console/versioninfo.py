"""
Version information view for the mitmproxy console UI.
"""

import os
import subprocess

import urwid

from mitmproxy import version
from mitmproxy.tools.console import layoutwidget


class VersionInfo(urwid.ListBox, layoutwidget.LayoutWidget):
    title = "Version Info"
    keyctx = "versioninfo"

    def __init__(self, master):
        self.master = master
        super().__init__(self._get_content())

    def _get_content(self):
        text = []

        text.append(urwid.Text([("title", "mitmproxy Version Information")]))
        text.append(urwid.Text(""))

        version_str = version.get_dev_version()
        text.append(urwid.Text([("head", "Version: "), ("text", version_str)]))
        text.append(urwid.Text(""))

        text.append(urwid.Text([("head", "Base Version: "), ("text", version.VERSION)]))
        text.append(urwid.Text(""))

        git_info = self._get_git_info()
        if git_info:
            text.append(urwid.Text([("title", "Git Information")]))
            text.append(urwid.Text(""))
            for key, value in git_info.items():
                text.append(urwid.Text([("head", f"{key}: "), ("text", value)]))
        else:
            text.append(
                urwid.Text([("head", "Git Information: "), ("text", "Not available")])
            )

        text.extend([urwid.Text("")] * 5)

        return urwid.SimpleFocusListWalker(text)

    def _get_git_info(self):
        """Returns a dict with git info or None if not in a git repository."""
        git_info = {}
        here = os.path.abspath(os.path.join(os.path.dirname(version.__file__), ".."))

        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=here,
                check=True,
            )

            commit_hash = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    stderr=subprocess.DEVNULL,
                    cwd=here,
                )
                .decode()
                .strip()
            )
            git_info["Commit Hash"] = commit_hash[:7]
            git_info["Full Commit Hash"] = commit_hash

            commit_date = (
                subprocess.check_output(
                    ["git", "log", "-1", "--format=%ci"],
                    stderr=subprocess.DEVNULL,
                    cwd=here,
                )
                .decode()
                .strip()
            )
            git_info["Commit Date"] = commit_date

            try:
                last_tag = (
                    subprocess.check_output(
                        ["git", "describe", "--tags", "--abbrev=0"],
                        stderr=subprocess.DEVNULL,
                        cwd=here,
                    )
                    .decode()
                    .strip()
                )
                git_info["Last Tag"] = last_tag
            except subprocess.CalledProcessError:
                pass

            try:
                branch = (
                    subprocess.check_output(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        stderr=subprocess.DEVNULL,
                        cwd=here,
                    )
                    .decode()
                    .strip()
                )
                git_info["Branch"] = branch
            except subprocess.CalledProcessError:
                pass

            return git_info if git_info else None
        except Exception:
            return None

    def keypress(self, size, key):
        if key == "m_end":
            self.set_focus(len(self.body) - 1)
        elif key == "m_start":
            self.set_focus(0)
        else:
            return super().keypress(size, key)
