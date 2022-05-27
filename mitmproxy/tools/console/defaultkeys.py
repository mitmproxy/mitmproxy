
def map(km):
    km.add("?", "console.view.help", ["quickhelp", "global"], "View help")
    km.add("q", "console.view.pop", ["quickhelp", "commonkey", "global"], "Exit the current view", "Exit View")
    km.add(":", "console.command ", ["quickhelp", "commonkey", "global"], "Command prompt", "Command Prompt")
    km.add("O", "console.view.options", ["quickhelp", "commonkey", "global"], "View options", "Options")
    km.add("E", "console.view.eventlog", ["commonkey", "global"], "View event log", "Event Log")
    km.add("enter", "console.nav.select", ["commonkey", "global"], "Select")
    km.add("tab", "console.nav.next", ["commonkey", "global"], "Next")

    km.add("?", "console.view.pop", ["help"], "Exit help")

    km.add("C", "console.view.commands", ["global"], "View commands", "Commands")
    km.add("P", "console.view.flow @focus", ["global"], "View flow details", "Flow Details")
    km.add("B", "browser.start", ["global"], "Start an attached browser", "Start Browser")
    km.add("K", "console.view.keybindings", ["global"], "View key bindings", "Key Bindings")
    km.add("-", "console.layout.cycle", ["global"], "Cycle to next layout", "Next Layout")
    km.add("shift tab", "console.panes.next", ["global"], "Focus next layout pane", "Next Layout Pane")
    km.add("ctrl right", "console.panes.next", ["global"], "Focus next layout pane", "Next Layout Pane")
    km.add("g", "console.nav.start", ["global"], "Go to start")
    km.add("G", "console.nav.end", ["global"], "Go to end", "Go To End")
    km.add("k", "console.nav.up", ["global"], "Up")
    km.add("j", "console.nav.down", ["global"], "Down")
    km.add("l", "console.nav.right", ["global"], "Right")
    km.add("h", "console.nav.left", ["global"], "Left")
    km.add("space", "console.nav.pagedown", ["global"], "Page down")
    km.add("ctrl f", "console.nav.pagedown", ["global"], "Page down")
    km.add("ctrl b", "console.nav.pageup", ["global"], "Page up")
    km.add(
        "I",
        "set intercept_active toggle",
        ["global"],
        "Toggle whether the filtering via the intercept option is enabled",
        "Toggle Intercept Option"
    )
    km.add("i", "console.command.set intercept", ["global"], "Set intercept")
    km.add("W", "console.command.set save_stream_file", ["global"], "Stream to file")


    km.add(
        "n",
        "console.command view.flows.create get https://example.com/",
        ["flowlist"],
        "Create a new flow",
        "New Flow"
    )
    km.add("D", "view.flows.duplicate @focus", ["flowlist", "flowview"], "Duplicate flow")
    km.add("X", "flow.kill @focus", ["flowlist"], "Kill this flow", "Kill Flow")
    km.add("f", "console.command.set view_filter", ["flowlist"], "Set view filter")
    km.add("F", "set console_focus_follow toggle", ["flowlist"], "Set focus follow")
    km.add("r", "replay.client @focus", ["flowlist", "flowview"], "Replay this flow", "Replay Flow")
    km.add("z", "view.flows.remove @all", ["flowlist"], "Clear flow list", "Clear List")
    km.add(
        "o",
        """
        console.choose.cmd Order view.order.options
        set view_order {choice}
        """,
        ["flowlist"],
        "Set flow list order",
        "Set List Order"
    )
    km.add("m", "flow.mark.toggle @focus", ["flowlist"], "Toggle mark on this flow", "Mark Flow")
    km.add("U", "flow.mark @all false", ["flowlist"], "Un-set all marks")
    km.add("S", "console.command replay.server ", ["flowlist"], "Start server replay")
    km.add("v", "set view_order_reversed toggle", ["flowlist"], "Reverse flow list order", "Reverse Flow List")
    km.add("Z", "view.flows.remove @hidden", ["flowlist"], "Purge all flows not showing", "Purge")
    km.add(
        "M",
        "view.properties.marked.toggle",
        ["flowlist"],
        "Toggle viewing marked flows",
    )
    km.add(
        "w",
        "console.command save.file @shown ",
        ["flowlist"],
        "Save listed flows to file",
    )

    km.add(
        "e",
        """
        console.choose.cmd Part console.edit.focus.options
        console.edit.focus {choice}
        """,
        ["flowview"],
        "Edit a flow component",
        "Edit Flow"
    )
    km.add(
        "V",
        "flow.revert @focus",
        ["flowlist", "flowview"],
        "Revert changes to this flow",
        "Revert Flow Changes"
    )
    km.add("p", "view.focus.prev", ["flowview"], "Go to previous flow", "Prev Flow")
    km.add("space", "view.focus.next", ["flowview"], "Go to next flow", "Next Flow")
    km.add("L", "console.command view.flows.load ", ["flowlist"], "Load flows from file", "Load Flows")
    km.add("w", "console.command save.file @focus ", ["flowview"], "Save flow to file", "Save Flow")
    km.add(
        "f",
        "view.settings.setval.toggle @focus fullcontents",
        ["flowview"],
        "Toggle viewing full contents on this flow",
    )
    km.add(
        "v",
        """
        console.choose "View Part" request,response
        console.bodyview @focus {choice}
        """,
        ["flowview"],
        "View flow body in an external viewer",
        "External View"
    )
    km.add(
        "m",
        """
        console.choose.cmd Mode console.flowview.mode.options
        console.flowview.mode.set {choice}
        """,
        ["flowview"],
        "Set flow view mode",
        "Set View Mode"
    )
    km.add(
        "z",
        """
        console.choose "Part" request,response
        flow.encode.toggle @focus {choice}
        """,
        ["flowview"],
        "Encode/decode flow body",
    )

    km.add(
        "|",
        "console.command script.run @focus ",
        ["flowlist", "flowview"],
        "Run a script on this flow",
        "Run Script On Flow"
    )
    km.add(
        "b",
        "console.command cut.save @focus response.content ",
        ["flowlist", "flowview"],
        "Save response body to file",
        "Save Response"
    )
    km.add(
        "d",
        "view.flows.remove @focus",
        ["flowlist", "flowview"],
        "Delete flow from view",
        "Delete From View"
    )
    km.add(
        "e",
        """
        console.choose.cmd Format export.formats
        console.command export.file {choice} @focus
        """,
        ["flowlist", "flowview"],
        "Export this flow to file",
    )
    km.add(
        ";",
        "console.command flow.comment @focus ''",
        ["flowlist", "flowview"],
        "Add comment to flow",
    )
    km.add(
        "A",
        "flow.resume @all",
        ["flowlist", "flowview"],
        "Resume all intercepted flows",
    )
    km.add(
        "a",
        "flow.resume @focus",
        ["flowlist", "flowview"],
        "Resume this intercepted flow",
    )
    km.add(
        "ctrl l",
        "console.command cut.clip ",
        ["flowlist", "flowview"],
        "Send cuts to clipboard",
    )

    km.add("L", "console.command options.load ", ["options"], "Load from file")
    km.add("S", "console.command options.save ", ["options"], "Save to file")
    km.add("D", "options.reset", ["options"], "Reset all options", "Reset All")
    km.add("d", "console.options.reset.focus", ["options"], "Reset this option", "Reset Option")

    km.add("a", "console.grideditor.add", ["grideditor"], "Add a row after cursor", "Add Row")
    km.add("A", "console.grideditor.insert", ["grideditor"], "Insert a row before cursor", "Insert Row")
    km.add("d", "console.grideditor.delete", ["grideditor"], "Delete this row", "Delete Row")
    km.add(
        "r",
        "console.command console.grideditor.load",
        ["grideditor"],
        "Read unescaped data into the current cell from file",
    )
    km.add(
        "R",
        "console.command console.grideditor.load_escaped",
        ["grideditor"],
        "Load a Python-style escaped string into the current cell from file",
    )
    km.add("e", "console.grideditor.editor", ["grideditor"], "Edit in external editor")
    km.add(
        "w",
        "console.command console.grideditor.save ",
        ["grideditor"],
        "Save data to file as CSV",
    )

    km.add("z", "eventstore.clear", ["eventlog"], "Clear")

    km.add(
        "a",
        """
        console.choose.cmd "Context" console.key.contexts
        console.command console.key.bind {choice}
        """,
        ["keybindings"],
        "Add a key binding",
        "Add"
    )
    km.add(
        "d",
        "console.key.unbind.focus",
        ["keybindings"],
        "Unbind the currently focused key binding",
        "Unbind"
    )
    km.add(
        "enter",
        "console.key.edit.focus",
        ["keybindings"],
        "Edit the currently focused key binding",
        "Edit"
    )
    km.add(
        "x",
        "console.key.execute.focus",
        ["keybindings"],
        "Execute the currently focused key binding",
        "Execute"
    )
