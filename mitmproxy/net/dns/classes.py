IN = 1
CH = 3
HS = 4
NONE = 254
ANY = 255

_STRINGS = {IN: "IN", CH: "CH", HS: "HS", NONE: "NONE", ANY: "ANY"}


def to_str(class_: int) -> str:
    return _STRINGS.get(class_, f"CLASS({class_})")
