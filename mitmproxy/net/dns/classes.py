IN = 1
CH = 3
HS = 4
NONE = 254
ANY = 255

_STRINGS = {
    IN: "IN",
    CH: "CH",
    HS: "HS",
    NONE: "NONE",
    ANY: "ANY"
}


def str(class_: int):
    return _STRINGS.get(class_, f"CLASS({class_})")
