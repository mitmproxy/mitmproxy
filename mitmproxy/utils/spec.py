import typing
from mitmproxy import flowfilter


def _match_all(flow) -> bool:
    return True


def parse_spec(option: str) -> typing.Tuple[flowfilter.TFilter, str, str]:
    """
    Parse strings in the following format:

        [/flow-filter]/subject/replacement

    """
    sep, rem = option[0], option[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        subject, replacement = parts
        return _match_all, subject, replacement
    elif len(parts) == 3:
        patt, subject, replacement = parts
        flow_filter = flowfilter.parse(patt)
        if not flow_filter:
            raise ValueError(f"Invalid filter pattern: {patt}")
        return flow_filter, subject, replacement
    else:
        raise ValueError("Invalid number of parameters (2 or 3 are expected)")
