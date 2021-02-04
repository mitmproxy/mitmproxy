import collections
from typing import Dict, Optional, Tuple


def parse_content_type(c: str) -> Optional[Tuple[str, str, Dict[str, str]]]:
    """
        A simple parser for content-type values. Returns a (type, subtype,
        parameters) tuple, where type and subtype are strings, and parameters
        is a dict. If the string could not be parsed, return None.

        E.g. the following string:

            text/html; charset=UTF-8

        Returns:

            ("text", "html", {"charset": "UTF-8"})
    """
    parts = c.split(";", 1)
    ts = parts[0].split("/", 1)
    if len(ts) != 2:
        return None
    d = collections.OrderedDict()
    if len(parts) == 2:
        for i in parts[1].split(";"):
            clause = i.split("=", 1)
            if len(clause) == 2:
                d[clause[0].strip()] = clause[1].strip()
    return ts[0].lower(), ts[1].lower(), d


def assemble_content_type(type, subtype, parameters):
    if not parameters:
        return f"{type}/{subtype}"
    params = "; ".join(
        f"{k}={v}"
        for k, v in parameters.items()
    )
    return "{}/{}; {}".format(
        type, subtype, params
    )
