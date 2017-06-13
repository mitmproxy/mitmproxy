import blinker

# Clear the eventlog
sig_clear_log = blinker.Signal()

# Add an entry to the eventlog
sig_add_log = blinker.Signal()


def add_log(e, level):
    sig_add_log.send(
        None,
        e=e,
        level=level
    )


# Show a status message in the action bar
status_message = blinker.Signal()

# Prompt for input
status_prompt = blinker.Signal()

# Prompt for a path
status_prompt_path = blinker.Signal()

# Prompt for a single keystroke
status_prompt_onekey = blinker.Signal()

# Prompt for a command
status_prompt_command = blinker.Signal()

# Call a callback in N seconds
call_in = blinker.Signal()

# Focus the body, footer or header of the main window
focus = blinker.Signal()

# Fired when settings change
update_settings = blinker.Signal()

# Fired when a flow changes
flow_change = blinker.Signal()

# Fired when the flow list or focus changes
flowlist_change = blinker.Signal()

# Pop and push view state onto a stack
pop_view_state = blinker.Signal()
push_view_state = blinker.Signal()

# Fired when the key bindings change
keybindings_change = blinker.Signal()
