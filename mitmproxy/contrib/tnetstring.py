import six

if six.PY2:
    from .py2.tnetstring import load, loads, dump, dumps
else:
    from .py3.tnetstring import load, loads, dump, dumps

__all__ = ["load", "loads", "dump", "dumps"]
