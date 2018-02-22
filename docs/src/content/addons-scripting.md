---
title: "Scripting"
menu:
    addons:
        weight: 5
---

# Scripting

Sometimes, we would like to write a quick script without going through the
trouble of creating a class. The addons mechanism has a shorthand that allows a
module as a whole to be treated as an addon object. This lets us place event
handler functions in the module scope. For instance, here is a complete script
that adds a header to every request.


{{< example src="examples/addons/scripting.py" lang="py" >}}