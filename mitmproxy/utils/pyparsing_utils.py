import pyparsing as pp

# Compatibility for pyparsing < 3.0.0
# We prefer the modern snake_case names if available, but fall back to camelCase for 2.4.2.

PP_MAJOR = int(pp.__version__.split(".")[0])


def set_parse_action(element: pp.ParserElement, action) -> pp.ParserElement:
    if PP_MAJOR >= 3:
        return element.set_parse_action(action)
    return element.setParseAction(action)


def leave_whitespace(element: pp.ParserElement) -> pp.ParserElement:
    if PP_MAJOR >= 3:
        return element.leave_whitespace()
    return element.leaveWhitespace()


def parse_string(
    element: pp.ParserElement, string: str, parse_all: bool = False
) -> pp.ParseResults:
    if PP_MAJOR >= 3:
        return element.parse_string(string, parse_all=parse_all)
    return element.parseString(string, parseAll=parse_all)


def infix_notation(*args, **kwargs):
    if PP_MAJOR >= 3:
        return pp.infix_notation(*args, **kwargs)
    return pp.infixNotation(*args, **kwargs)


def QuotedString(
    quote_char: str, esc_char: str | None = None, **kwargs
) -> pp.QuotedString:
    if esc_char is not None:
        if PP_MAJOR >= 3:
            kwargs["esc_char"] = esc_char
        else:
            kwargs["escChar"] = esc_char
    return pp.QuotedString(quote_char, **kwargs)
