import os
from typing import Callable, Optional

import urwid
from mitmproxy.tools.console import signals
from mitmproxy.tools.console.grideditor import base
from mitmproxy.utils import strutils


def read_file(filename: str, callback: Callable[..., None], escaped: bool) -> Optional[str]:
    if not filename:
        return

    filename = os.path.expanduser(filename)
    try:
        with open(filename, "r" if escaped else "rb") as f:
            d = f.read()
    except IOError as v:
        return str(v)

    if escaped:
        try:
            d = strutils.escaped_str_to_bytes(d)
        except ValueError:
            return "Invalid Python-style string encoding."
    # TODO: Refactor the status_prompt_path signal so that we
    # can raise exceptions here and return the content instead.
    callback(d)


class Column(base.Column):
    def Display(self, data):
        return Display(data)

    def Edit(self, data):
        return Edit(data)

    def blank(self):
        return b""

    def keypress(self, key, editor):
        if key == "r":
            if editor.walker.get_current_value() is not None:
                signals.status_prompt_path.send(
                    self,
                    prompt="Read file",
                    callback=read_file,
                    args=(editor.walker.set_current_value, True)
                )
        elif key == "R":
            if editor.walker.get_current_value() is not None:
                signals.status_prompt_path.send(
                    self,
                    prompt="Read unescaped file",
                    callback=read_file,
                    args=(editor.walker.set_current_value, False)
                )
        elif key == "e":
            o = editor.walker.get_current_value()
            if o is not None:
                n = editor.master.spawn_editor(o)
                n = strutils.clean_hanging_newline(n)
                editor.walker.set_current_value(n)
        elif key in ["enter"]:
            editor.walker.start_edit()
        else:
            return key


class Display(base.Cell):
    def __init__(self, data: bytes):
        self.data = data
        escaped = strutils.bytes_to_escaped_str(data)
        w = urwid.Text(escaped, wrap="any")
        super().__init__(w)

    def get_data(self) -> bytes:
        return self.data


class Edit(base.Cell):
    def __init__(self, data: bytes):
        data = strutils.bytes_to_escaped_str(data)
        w = urwid.Edit(edit_text=data, wrap="any", multiline=True)
        w = urwid.AttrWrap(w, "editfield")
        super().__init__(w)

    def get_data(self) -> bytes:
        txt = self._w.get_text()[0].strip()
        try:
            return strutils.escaped_str_to_bytes(txt)
        except ValueError:
            signals.status_message.send(
                self,
                message="Invalid Python-style string encoding.",
                expire=1000
            )
            raise
