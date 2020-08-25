#!/usr/bin/env python3

import os
import requests
from urllib3.exceptions import InsecureRequestWarning

from clidirector import MitmCliDirector


def record_user_interface(d: MitmCliDirector):
    tmux = d.start_session(width=100, height=26)
    window = tmux.attached_window

    window.set_window_option("window-status-current-format", "mitmproxy Tutorial: User Interface")

    d.exec("mitmproxy")
    d.pause(4)
    d.init_flow_list(step="user_interface")
    d.pause(2)

    d.start_recording("recordings/mitmproxy_user_interface.cast")
    d.instruction(
        title="mitmproxy's views: Default view",
        instruction="You should see the default view of mitmproxy, which shows a table-like list of flows. Every line represents a request and (optionally) its response using columns.",
        duration=4,
        time_from=0.5
    )
    d.pause(4)

    d.instruction(
        title="Controlling mitmproxy",
        instruction="mitmproxy is controlled using keyboard shortcuts. 1.Use your arrow keys 🠗 and 🠕 to change the focused flow (>>). 2. Put the focus on the flow requesting /votes. 3. Press ENTER to view the details of the flow.",
        duration=6
    )
    d.press_key("Down", count=4, pause=0.5)
    d.press_key("Up", count=2, pause=0.5)
    d.press_key("Down", count=2, pause=0.5)
    d.press_key("Up", count=2, pause=0.5)
    d.pause(1)
    d.press_key("Enter")
    d.pause(1)

    d.instruction(
        "mitmproxy's views: Flow details view",
        "You are now in the flow details view of the flow that requested /votes. The flow details view has 3 panes: request, response, and detail. Use your arrow keys 🠔 and 🠖 to switch between panes.",
        6
    )
    d.pause(1)
    d.press_key("Right", count=2, pause=2)
    d.press_key("Left", count=2, pause=0.5)

    d.instruction(
        "mitmproxy's views: Exit a view",
        "Press 'q' to exit the current view.",
        3
    )
    d.pause(3)
    d.type("q")

    d.instruction(
        "Keyboard Shortcuts",
        "Press '?' to view a list of all available keyboard shortcuts in the current view. If you only remember one shortcut, it should be this one.",
        3
    )
    d.pause(3)
    d.press_key("?", count=2, pause=1)
    d.pause(3)
    d.press_key("Down", count=15, pause=0.25)
    d.pause(3)

    d.type("qy")
    d.pause(0.5)
    d.save_instructions("recordings/mitmproxy_user_interface_instructions.json")
    d.end()


def record_user_interface2(d: MitmCliDirector):
    tmux = d.start_session(width=100, height=26)
    window = tmux.attached_window

    window.set_window_option("window-status-current-format", "mitmproxy Tutorial: User Interface")

    d.exec("mitmproxy")
    d.pause(4)
    d.init_flow_list(step="whats_next")
    d.pause(2)

    d.start_recording("recordings/mitmproxy_whats_next.cast")
    d.message(msg="1. This is the default view of mitmproxy.", add_instruction=True
    )
    d.message("2. Every line represents a request and its response.", add_instruction=True)
    d.message("3. mitmproxy is controlled using keyboard shortcuts.", add_instruction=True)
    d.message(
        msg="4. Use your arrow keys UP and DOWN to change the focused flow (>>).",
        instruction_html="4. Use your arrow keys <kbd>🠕</kbd> and <kbd>🠗</kbd> to change the focused flow (<code>&gt;&gt;</code>)."
    )
    d.press_key("Down", count=4, pause=0.75)
    d.press_key("Up", count=2, pause=0.75)
    d.press_key("Down", count=2, pause=0.75)

    d.message(
        "5. Press ENTER to view the details of the focused flow.",
        instruction_html="5. Press <kbd>↵</kbd> to view the details of the focused flow."
    )
    d.press_key("Enter")

    d.message("6. The flow details view has 3 panes: request, response, and detail.", add_instruction=True)
    d.message(
        msg="7. Use your LEFT and RIGHT arrow keys to switch between panes.",
        instruction_html="7. Use your <kbd>🠔</kbd> and <kbd>🠖</kbd> arrow keys to switch between panes.")
    d.press_key("Right", count=2, pause=2.5)
    d.press_key("Left", count=2, pause=0.5)

    d.message(
        msg="8. Press 'q' to exit the current view.",
        instruction_html="8. Press <kbd>q</kbd> to exit the current view."
    )
    d.type("q")

    d.message(
        msg="9. Press '?' to view a list of all available keyboard shortcuts.",
        instruction_html="9. Press <kbd>?</kbd> to view a list of all available keyboard shortcuts."
    )
    d.type("?")
    d.pause(3)
    d.press_key("Down", count=15, pause=0.25)

    d.message(
        msg="10. The '?' shortcut works in every view - you should remember it.",
        instruction_html="10. The <kbd>?</kbd> shortcut works in every view - you should remember it."
    )
    d.message("11. You now know the basics of mitmproxy's UI.", add_instruction=True)
    d.pause(1)
    d.save_instructions("recordings/mitmproxy_whats_next_instructions.json")
    d.end()
