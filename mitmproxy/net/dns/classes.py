IN = 1
CH = 3
HS = 4
NONE = 254
ANY = 255

_STRINGS = {IN: "IN", CH: "CH", HS: "HS", NONE: "NONE", ANY: "ANY"}
_INTS = {v: k for k, v in _STRINGS.items()}


def to_str(class_: int) -> str:
    return _STRINGS.get(class_, f"CLASS({class_})")


def from_str(class_: str) -> int:
    try:
        return _INTS[class_]
    except KeyError:
        return int(class_.removeprefix("CLASS(").removesuffix(")"))
