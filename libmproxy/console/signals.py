import blinker

# Show a status message in the action bar
status_message = blinker.Signal()

# Prompt for input
status_prompt = blinker.Signal()

# Prompt for a path
status_prompt_path = blinker.Signal()

# Prompt for a single keystroke
status_prompt_onekey = blinker.Signal()

# Call a callback in N seconds
call_in = blinker.Signal()

# Focus the body, footer or header of the main window
focus = blinker.Signal()
