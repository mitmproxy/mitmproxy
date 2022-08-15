from __future__ import annotations
from mitmproxy.utils import signals


# Show a status message in the action bar
def _status_message(message: tuple[str, str] | str, expire: int | None = None) -> None:
    ...


status_message = signals.SyncSignal(_status_message)

# Prompt for input
status_prompt = signals.SyncSignal(lambda prompt, text, callback, args=(): None)

# Prompt for a single keystroke
status_prompt_onekey = signals.SyncSignal(lambda prompt, keys, callback, args=(): None)


# Prompt for a command
def _status_prompt_command(partial: str = "", cursor: int | None = None) -> None:
    ...


status_prompt_command = signals.SyncSignal(_status_prompt_command)

# Call a callback in N seconds
call_in = signals.SyncSignal(lambda seconds, callback, args=(): None)

# Focus the body, footer or header of the main window
focus = signals.SyncSignal(lambda section: None)

# Fired when settings change
update_settings = signals.SyncSignal(lambda: None)

# Fired when a flow changes
flow_change = signals.SyncSignal(lambda flow: None)

# Pop and push view state onto a stack
pop_view_state = signals.SyncSignal(lambda: None)

# Fired when the key bindings change
keybindings_change = signals.SyncSignal(lambda: None)
