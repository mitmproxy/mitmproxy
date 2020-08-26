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
    d.pause(5)
    d.init_flow_list(step="user_interface")

    d.start_recording("recordings/mitmproxy_user_interface.cast")
    d.message("This is the default view of mitmproxy.")
    d.message("Every line represents a request and its response.")
    d.message("mitmproxy adds rows to the view as new requests come in.")
    d.message("Generate some requests by voting for your favorite pet on the right.")
    d.request("http://tutorial.mitm.it/vote/dog")
    d.pause(3)
    d.request("http://tutorial.mitm.it/vote/dog")
    d.pause(3)
    d.request("http://tutorial.mitm.it/vote/dog")
    d.pause(1)
    d.message("You see the voting requests in the list of flows.")

    d.message("mitmproxy is controlled using keyboard shortcuts.")
    d.message(
        msg="Use your arrow keys UP and DOWN to change the focused flow (>>).",
        instruction_html="Use <kbd>🠕</kbd> and <kbd>🠗</kbd> to change the focused flow (<code>&gt;&gt;</code>)."
    )
    d.press_key("Down", count=4, pause=0.5)
    d.press_key("Up", count=2, pause=0.5)
    d.press_key("Down", count=9, pause=0.5)

    d.message("The focused flow is used as a target for various commands.")

    d.message(
        msg="One such command views the flow details, it is bound to ENTER.",
        instruction_html="One such command views the flow details, it is bound to <kbd>↵</kbd>."
    )

    d.message(
        msg="Press ENTER to view the details of the focused flow.",
        instruction_html="Press <kbd>↵</kbd> to view the details of the focused flow."
    )
    d.press_key("Enter")

    d.message("The flow details view has 3 panes: request, response, and detail.")
    d.message(
        msg="Use your LEFT and RIGHT arrow keys to switch between panes.",
        instruction_html="Use <kbd>🠔</kbd> and <kbd>🠖</kbd> to switch panes.")
    d.press_key("Right", count=2, pause=2.5)
    d.press_key("Left", count=2, pause=1)

    d.message(
        msg="Press 'q' to exit the current view.",
        instruction_html="Press <kbd>q</kbd> to exit the current view."
    )
    d.type("q")

    d.message(
        msg="Press '?' to get a list of all available keyboard shortcuts.",
        instruction_html="Press <kbd>?</kbd> to get a list of all keyboard shortcuts."
    )
    d.type("?")
    d.pause(2)
    d.press_key("Down", count=20, pause=0.25)

    d.message(
        msg="Press 'q' to exit the current view.",
        instruction_html="Press <kbd>q</kbd> to exit the current view."
    )
    d.type("q")

    d.message("Each shortcut is internally bound to a command.")
    d.message("You can also execute commands directly (without using shortcuts).")
    d.message(
        msg="Press ':' to open the command prompt.",
        instruction_html="Press <kbd>:</kbd> to open the command prompt.",
    )
    d.type(":")

    d.message(
        msg="Enter 'console.view.flow @focus'.",
        instruction_html="Enter <kbd>console.view.flow @focus</kbd>.",
    )
    d.type("console.view.flow @focus")

    d.message(
        msg="The command 'console.view.flow' opens the details view for a flow.",
        instruction_html="The command <code>console.view.flow</code> opens the details view for a flow.",
    )

    d.message(
        msg="The argument '@focus' defines the target flow.",
        instruction_html="The argument <code>@focus'</code> defines the target flow.",
    )

    d.message(
        msg="Press ENTER to execute the command.",
        instruction_html="Press <kbd>↵</kbd> to execute the command.",
    )
    d.press_key("Enter")

    d.message("Commands unleash the full power of mitmproxy.")

    d.message("You now know basics of mitmproxy's UI and how to control it.")
    d.pause(1)
    d.save_instructions("recordings/mitmproxy_user_interface_instructions.json")
    d.end()


#todo: interception does not work with asgiapp
def record_intercept_requests(d: MitmCliDirector):
    tmux = d.start_session(width=100, height=26)
    window = tmux.attached_window

    window.set_window_option("window-status-current-format", "mitmproxy Tutorial: Intercept Requests")

    # prepare view
    d.exec("mitmproxy")
    d.pause(5)
    d.init_flow_list(step="intercept_requests")

    d.start_recording("recordings/mitmproxy_intercept_requests.cast")

    d.message(
        msg="""Press 'i' to prepopulate mitmproxy's command prompt with "set intercept ''".""",
        instruction_html="Press <kbd>i</kbd> to prepopulate mitmproxy's command prompt with <code>set intercept ''</code>."
    )
    d.type("i")
    d.pause(2)

    d.message(
        msg="Enter '~u /vote/' between the quotes of the 'set intercept' command and press ENTER.",
        instruction_html="Enter <kbd>~u /vote/</kbd> between the quotes of the <code>set intercept</code> command and press <kbd>↵</kbd>."
    )
    d.exec("~u /vote/")

    d.message("Submit a vote in the voting app on the right.")
    d.request("http://tutorial.mitm.it/vote/cat", threaded=True)
    d.pause(2)

    d.message("You will see a new line in in the list of flows.")
    d.message(
        msg="The new flow is colored in red to indicate that it has been intercepted.",
        instruction_html="""The new flow is colored in <span class="text-danger">red</span> to indicate that it has been intercepted."""
    )

    d.message(
        msg="Put the focus (>>) on the intercepted flow.",
        instruction_html="Put the focus (<code>&gt;&gt;</code>) on the intercepted flow."
    )
    d.press_key("Down", count=11, pause=0.25)

    d.message(
        msg="Press 'a' to resume this flow without making any changes.",
        instruction_html="Press <kbd>a</kbd> to resume this flow without making any changes."
    )
    d.type("a")

    d.message("Submit another vote and focus its flow.")
    d.request("http://tutorial.mitm.it/vote/dog", threaded=True)
    d.pause(2)
    d.press_key("Down")

    d.message(
        msg="Press 'X' to kill this flow, i.e., discard it without forwarding it to the server.",
        instruction_html="Press <kbd>X</kbd> to kill this flow, i.e., discard it without forwarding it to the server."
    )
    d.type("X")
    d.pause(3)
    d.save_instructions("recordings/mitmproxy_intercept_requests_instructions.json")
    d.end()


def record_modify_requests(d: MitmCliDirector):
    tmux = d.start_session(width=100, height=26)
    window = tmux.attached_window

    window.set_window_option("window-status-current-format", "mitmproxy Tutorial: Modify Requests")

    # prepare view
    d.exec("mitmproxy")
    d.pause(5)
    d.init_flow_list(step="modify_requests")
    d.type("i")
    d.exec("~u /vote/")

    d.start_recording("recordings/mitmproxy_modify_requests.cast")

    d.message("We assume that the interception rule from the previous step is still configured.")
    d.message("Submit a vote in the voting app on the right.")
    d.request("http://tutorial.mitm.it/vote/cat", threaded=True)

    d.message("We now want to modify the intercepted request.")
    d.message(
        msg="Put the focus (>>) on the intercepted flow.",
        instruction_html="Put the focus (<code>&gt;&gt;</code>) on the intercepted flow."
    )
    d.press_key("Down", count=11, pause=0.25)

    d.message(
        "Press ENTER to open the details view for the intercepted flow.",
        instruction_html="Press <kbd>↵</kbd> to open the details view for the intercepted flow."
    )
    d.press_key("Enter")

    d.message(
        "Press 'e' to edit the intercepted flow.",
        instruction_html="Press <kbd>e</kbd> to edit the intercepted flow."
    )
    d.type("e")

    d.message("mitmproxy asks which part to modify.")

    d.message(
        msg="Select 'path' by using your arrow keys and press ENTER.",
        instruction_html="Select 'path' by using your arrow keys and press <kbd>↵</kbd>.",
    )
    d.press_key("Down", count=3, pause=0.5)
    d.pause(1)
    d.press_key("Enter")

    d.message(
        msg="Use your arrow keys to select the pet and press ENTER.",
        instruction_html="Use your arrow keys to select the pet and press <kbd>↵</kbd>."
    )
    d.press_key("Down", pause=2)
    d.press_key("Enter")

    d.message(
        msg="Replace 'dog' with 'cat', or vice versa.",
        instruction_html="Replace <kbd>dog</kbd> with <kbd>cat</kbd>, or vice versa."
    )
    d.press_key("BSpace", count=3, pause=0.5)
    d.type("dog", pause=0.5)

    d.message(
        msg="Press ESC to confirm your change.",
        instruction_html="Press <kbd>ESC</kbd> to confirm your change."
    )
    d.press_key("Escape")

    d.message(
        msg="Press 'q' to go back to the flow details view.",
        instruction_html="Press <kbd>q</kbd> to go back to the flow details view."
    )
    d.type("q")

    d.message(
        msg="Press 'a' to resume this flow.",
        instruction_html="Press <kbd>a</kbd> to resume this flow."
    )
    d.type("a")

    d.save_instructions("recordings/mitmproxy_modify_requests_instructions.json")
    d.end()


def record_replay_requests(d: MitmCliDirector):
    tmux = d.start_session(width=100, height=26)
    window = tmux.attached_window

    window.set_window_option("window-status-current-format", "mitmproxy Tutorial: Replay Requests")

    # prepare view
    d.exec("mitmproxy")
    d.pause(5)
    d.init_flow_list(step="replay_requests")

    d.start_recording("recordings/mitmproxy_replay_requests.cast")

    d.message("We use client-side replays to get our pet some more votes.")
    d.message("First, generate a vote for your favorite pet.")
    d.request("http://tutorial.mitm.it/vote/cat")
    d.pause(2)
    d.message(
        msg="Put the focus (>>) on the vote request.",
        instruction_html="Put the focus (<code>&gt;&gt;</code>) on the vote request."
    )
    d.press_key("Down", count=11, pause=0.25)

    d.message(
        msg="Press 'r' to replay this flow.",
        instruction_html="Press <kbd>r</kbd> to resume this flow."
    )
    d.type("r")
    d.message("Note: No new rows are added for replayed flows, but the existing row is updated.")

    d.message(
        msg="Press 'r' again multiple times to make sure your pet wins.",
        instruction_html="Press <kbd>r</kbd> again multiple times to make sure your pet wins."
    )
    d.press_key("r", count=5, pause=1)

    d.message("Click on 'Refresh Votes' on the right.")
    d.request("http://tutorial.mitm.it/votes")
    d.pause(2)
    d.message("The vote count increased due to the replays.")

    d.message("You can also modify a flow before replaying it.")
    d.message("It works as shown in the previous step.")

    d.save_instructions("recordings/mitmproxy_replay_requests_instructions.json")
    d.end()
