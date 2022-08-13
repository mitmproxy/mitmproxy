from mitmproxy.utils import signals


# Show a status message in the action bar
status_message = signals.SyncSignal()

# Prompt for input
status_prompt = signals.SyncSignal()

# Prompt for a path
status_prompt_path = signals.SyncSignal()

# Prompt for a single keystroke
status_prompt_onekey = signals.SyncSignal()

# Prompt for a command
status_prompt_command = signals.SyncSignal()

# Call a callback in N seconds
call_in = signals.SyncSignal()

# Focus the body, footer or header of the main window
focus = signals.SyncSignal()

# Fired when settings change
update_settings = signals.SyncSignal()

# Fired when a flow changes
flow_change = signals.SyncSignal()

# Fired when the flow list or focus changes
flowlist_change = signals.SyncSignal()

# Pop and push view state onto a stack
pop_view_state = signals.SyncSignal()
push_view_state = signals.SyncSignal()

# Fired when the key bindings change
keybindings_change = signals.SyncSignal()
