import six

if six.PY2:
    from .py2.tnetstring import load, loads, dump, dumps, pop
else:
    from .py3.tnetstring import load, loads, dump, dumps, pop

__all__ = ["load", "loads", "dump", "dumps", "pop"]
