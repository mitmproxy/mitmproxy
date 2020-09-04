#!/usr/bin/env python3

from clidirector import CliDirector


def record_user_interface(d: CliDirector):
    tmux = d.start_session(width=120, height=36)
    window = tmux.attached_window

    d.start_recording("recordings/mitmproxy_user_interface.cast")
    d.message("Welcome to the mitmproxy tutorial. In this lesson we cover the user interface.")
    d.pause(1)
    d.exec("mitmproxy")
    d.pause(3)

    d.message("This is the default view of mitmproxy.")
    d.message("mitmproxy adds rows to the view as new requests come in.")
    d.message("Let’s generate some requests using `curl` in a separate terminal.")

    pane_top = d.current_pane
    pane_bottom = window.split_window(attach=True)
    pane_bottom.resize_pane(height=12)

    d.focus_pane(pane_bottom)
    d.pause(2)

    d.type("curl")
    d.message("Use curl’s `--proxy` option to configure mitmproxy as a proxy.")
    d.type(" --proxy http://127.0.0.1:8080")

    d.message("We use the text-based weather service `wttr.in`.")
    d.exec(" \"http://wttr.in/Dunedin?0\"")

    d.pause(2)
    d.press_key("Up")
    d.press_key("Left", count=3)
    d.press_key("BSpace", count=7)
    d.exec("Innsbruck")

    d.pause(2)
    d.exec("exit", target=pane_bottom)

    d.focus_pane(pane_top)

    d.message("You see the requests to `wttr.in` in the list of flows.")

    d.message("mitmproxy is controlled using keyboard shortcuts.")
    d.message("Use your arrow keys `↑` and `↓` to change the focused flow (`>>`).")
    d.press_key("Down", pause=0.5)
    d.press_key("Up", pause=0.5)
    d.press_key("Down", pause=0.5)
    d.press_key("Up", pause=0.5)

    d.message("The focused flow (`>>`) is used as a target for various commands.")

    d.message("One such command shows the flow details, it is bound to `ENTER`.")

    d.message("Press `ENTER` to view the details of the focused flow.")
    d.press_key("Enter")

    d.message("The flow details view has 3 panes: request, response, and detail.")
    d.message("Use your arrow keys `←` and `→` to switch between panes.")
    d.press_key("Right", count=2, pause=2.5)
    d.press_key("Left", count=2, pause=1)

    d.message("Press `q` to exit the current view.",)
    d.type("q")

    d.message("Press `?` to get a list of all available keyboard shortcuts.")
    d.type("?")
    d.pause(2)
    d.press_key("Down", count=20, pause=0.25)

    d.message("Tip: Remember the `?` shortcut. It works in every view.")
    d.message("Press `q` to exit the current view.")
    d.type("q")

    d.message("Each shortcut is internally bound to a command.")
    d.message("You can also execute commands directly (without using shortcuts).")
    d.message("Press `:` to open the command prompt at the bottom.")
    d.type(":")

    d.message("Enter `console.view.flow @focus`.")
    d.type("console.view.flow @focus")

    d.message("The command `console.view.flow` opens the details view for a flow.")

    d.message("The argument `@focus` defines the target flow.")

    d.message("Press `ENTER` to execute the command.")
    d.press_key("Enter")

    d.message("Commands unleash the full power of mitmproxy, i.e., to configure interceptions.")

    d.message("You now know basics of mitmproxy’s UI and how to control it.")
    d.pause(1)

    d.message("In the next lesson you will learn to intercept flows.")
    d.save_instructions("recordings/mitmproxy_user_interface_instructions.json")
    d.end()


def record_intercept_requests(d: CliDirector):
    tmux = d.start_session(width=120, height=36)
    window = tmux.attached_window

    d.start_recording("recordings/mitmproxy_intercept_requests.cast")
    d.message("Welcome to the mitmproxy tutorial. In this lesson we cover the interception of requests.")
    d.pause(1)
    d.exec("mitmproxy")
    d.pause(3)

    d.message("We first need to configure mitmproxy to intercept requests.")

    d.message("Press `i` to prepopulate mitmproxy’s command prompt with `set intercept ''`.")
    d.type("i")
    d.pause(2)

    d.message("We use the flow filter expression `~u <regex>` to only intercept specific URLs.")
    d.message("Additionally, we use the filter `~q` to only intercept requests, but not responses.")
    d.message("We combine both flow filters using `&`.")

    d.message("Enter `~u /Dunedin & ~q` between the quotes of the `set intercept` command and press `ENTER`.")
    d.exec("~u /Dunedin & ~q")
    d.message("The bottom bar shows that the interception has been configured.")

    d.message("Let’s generate a request using `curl` in a separate terminal.")

    pane_top = d.current_pane
    pane_bottom = window.split_window(attach=True)
    pane_bottom.resize_pane(height=12)

    d.focus_pane(pane_bottom)
    d.pause(2)

    d.exec("curl --proxy http://127.0.0.1:8080 \"http://wttr.in/Dunedin?0\"")
    d.pause(2)

    d.focus_pane(pane_top)

    d.message("You see a new line in in the list of flows.")
    d.message("The new flow is displayed in red to indicate that it has been intercepted.")
    d.message("Put the focus (`>>`) on the intercepted flow. This is already the case in our example.")
    d.message("Press `a` to resume this flow without making any changes.")
    d.type("a")
    d.pause(2)

    d.focus_pane(pane_bottom)

    d.message("Submit another request and focus its flow.")
    d.press_key("Up")
    d.press_key("Enter")
    d.pause(2)

    d.focus_pane(pane_top)
    d.press_key("Down")
    d.pause(1)

    d.message("Press `X` to kill this flow, i.e., discard it without forwarding it to its final destination `wttr.in`.")
    d.type("X")
    d.pause(3)

    d.message("In the next lesson you will learn to modify intercepted flows.")
    d.save_instructions("recordings/mitmproxy_intercept_requests_instructions.json")
    d.end()


def record_modify_requests(d: CliDirector):
    tmux = d.start_session(width=120, height=36)
    window = tmux.attached_window

    d.start_recording("recordings/mitmproxy_modify_requests.cast")
    d.message("Welcome to the mitmproxy tutorial. In this lesson we cover the modification of intercepted requests.")
    d.pause(1)
    d.exec("mitmproxy")
    d.pause(3)

    d.message("We configure and use the same interception rule as in the last tutorial.")
    d.message("Press `i` to prepopulate mitmproxy’s command prompt, enter the flow filter `~u /Dunedin & ~q`, and press `ENTER`.")
    d.type("i")
    d.pause(2)
    d.exec("~u /Dunedin & ~q")

    d.message("Let’s generate a request using `curl` in a separate terminal.")

    pane_top = d.current_pane
    pane_bottom = window.split_window(attach=True)
    pane_bottom.resize_pane(height=12)

    d.focus_pane(pane_bottom)
    d.pause(2)

    d.exec("curl --proxy http://127.0.0.1:8080 \"http://wttr.in/Dunedin?0\"")
    d.pause(2)

    d.focus_pane(pane_top)

    d.message("We now want to modify the intercepted request.")
    d.message("Put the focus (`>>`) on the intercepted flow. This is already the case in our example.")

    d.message("Press `ENTER` to open the details view for the intercepted flow.")
    d.press_key("Enter")

    d.message("Press `e` to edit the intercepted flow.")
    d.type("e")

    d.message("mitmproxy asks which part to modify.")

    d.message("Select `path` by using your arrow keys and press `ENTER`.")
    d.press_key("Down", count=3, pause=0.5)
    d.pause(1)
    d.press_key("Enter")

    d.message("mitmproxy shows all path components line by line, in our example its just `Dunedin`.")
    d.message("Press `ENTER` to modify the selected path component.")
    d.press_key("Down", pause=2)
    d.press_key("Enter")

    d.message("Replace `Dunedin` with `Innsbruck`.")
    d.press_key("BSpace", count=7, pause=0.5)
    d.type("Innsbruck", pause=0.5)

    d.message("Press `ESC` to confirm your change.")
    d.press_key("Escape")

    d.message("Press `q` to go back to the flow details view.")
    d.type("q")

    d.message("Press `a` to resume the intercepted flow.")
    d.type("a")
    d.pause(2)

    d.message("You see that the request URL was modified and `wttr.in` replied with the weather report for `Innsbruck`.")

    d.message("In the next lesson you will learn to replay flows.")
    d.save_instructions("recordings/mitmproxy_modify_requests_instructions.json")
    d.end()


def record_replay_requests(d: CliDirector):
    tmux = d.start_session(width=120, height=36)
    window = tmux.attached_window

    d.start_recording("recordings/mitmproxy_replay_requests.cast")
    d.message("Welcome to the mitmproxy tutorial. In this lesson we cover replaying requests.")
    d.pause(1)
    d.exec("mitmproxy")
    d.pause(3)

    d.message("Let’s generate a request that we can replay. We use `curl` in a separate terminal.")

    pane_top = d.current_pane
    pane_bottom = window.split_window(attach=True)
    pane_bottom.resize_pane(height=12)

    d.focus_pane(pane_bottom)
    d.pause(2)

    d.exec("curl --proxy http://127.0.0.1:8080 \"http://wttr.in/Dunedin?0\"")
    d.pause(2)

    d.focus_pane(pane_top)

    d.message("We now want to replay the this request.")
    d.message("Put the focus (`>>`) on the request that should be replayed. This is already the case in our example.")
    d.message("Press `r` to replay the request.")
    d.type("r")

    d.message("Note that no new rows are added for replayed flows, but the existing row is updated.")
    d.message("Every time you press `r`, mitmproxy sends this request to the server again and updates the flow.")
    d.press_key("r", count=4, pause=1)

    d.message("You can also modify a flow before replaying it.")
    d.message("It works as shown in the previous lesson, by pressing `e`.")

    d.message("Congratulations! You have completed all lessons of the mitmproxy tutorial.")
    d.save_instructions("recordings/mitmproxy_replay_requests_instructions.json")
    d.end()
