from __future__ import annotations

from collections.abc import Callable
from typing import Union

from mitmproxy.utils import signals

StatusMessage = Union[tuple[str, str], str]


# Show a status message in the action bar
# Instead of using this signal directly, consider emitting a log event.
def _status_message(message: StatusMessage, expire: int = 5) -> None: ...


status_message = signals.SyncSignal(_status_message)


# Prompt for input
def _status_prompt(
    prompt: str, text: str | None, callback: Callable[[str], None]
) -> None: ...


status_prompt = signals.SyncSignal(_status_prompt)


# Prompt for a single keystroke
def _status_prompt_onekey(
    prompt: str, keys: list[tuple[str, str]], callback: Callable[[str], None]
) -> None: ...


status_prompt_onekey = signals.SyncSignal(_status_prompt_onekey)


# Prompt for a command
def _status_prompt_command(partial: str = "", cursor: int | None = None) -> None: ...


status_prompt_command = signals.SyncSignal(_status_prompt_command)


# Call a callback in N seconds
def _call_in(seconds: float, callback: Callable[[], None]) -> None: ...


call_in = signals.SyncSignal(_call_in)

# Focus the body, footer or header of the main window
focus = signals.SyncSignal(lambda section: None)

# Fired when settings change
update_settings = signals.SyncSignal(lambda: None)

# Fired when a flow changes
flow_change = signals.SyncSignal(lambda flow: None)

# Pop and push view state onto a stack
pop_view_state = signals.SyncSignal(lambda: None)

# Fired when the window state changes
window_refresh = signals.SyncSignal(lambda: None)

# Fired when the key bindings change
keybindings_change = signals.SyncSignal(lambda: None)
