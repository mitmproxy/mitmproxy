.. _replacements:

Replacements
============

Mitmproxy lets you specify an arbitrary number of patterns that define text
replacements within flows. Each pattern has 3 components: a filter that defines
which flows a replacement applies to, a regular expression that defines what
gets replaced, and a target value that defines what is substituted in.

Replace hooks fire when either a client request or a server response is
received. Only the matching flow component is affected: so, for example, if a
replace hook is triggered on server response, the replacement is only run on
the Response object leaving the Request intact. You control whether the hook
triggers on the request, response or both using the filter pattern. If you need
finer-grained control than this, it's simple to create a script using the
replacement API on Flow components.

Replacement hooks are extremely handy in interactive testing of applications.
For instance you can use a replace hook to replace the text "XSS" with a
complicated XSS exploit, and then "inject" the exploit simply by interacting
with the application through the browser. When used with tools like Firebug and
mitmproxy's own interception abilities, replacement hooks can be an amazingly
flexible and powerful feature.


On the command-line
-------------------

The replacement hook command-line options use a compact syntax to make it easy
to specify all three components at once. The general form is as follows:

.. code-block:: none

    /patt/regex/replacement

Here, **patt** is a mitmproxy filter expression, **regex** is a valid Python
regular expression, and **replacement** is a string literal. The first
character in the expression (``/`` in this case) defines what the separation
character is. Here's an example of a valid expression that replaces "foo" with
"bar" in all requests:

.. code-block:: none

    :~q:foo:bar

In practice, it's pretty common for the replacement literal to be long and
complex. For instance, it might be an XSS exploit that weighs in at hundreds or
thousands of characters. To cope with this, there's a variation of the
replacement hook specifier that lets you load the replacement text from a file.
So, you might start **mitmdump** as follows:

>>> mitmdump --replace-from-file :~q:foo:~/xss-exploit

This will load the replacement text from the file ``~/xss-exploit``.

Both the :option:`--replace` and :option:`--replace-from-file` flags can be passed multiple
times.


Interactively
-------------

The :kbd:`R` shortcut key in the mitmproxy options menu (:kbd:`o`) lets you add and edit
replacement hooks using a built-in editor. The context-sensitive help (:kbd:`?`) has
complete usage information.

================== =============================
command-line       :option:`--replace`,
                   :option:`--replace-from-file`
mitmproxy shortcut :kbd:`o` then :kbd:`R`
================== =============================
