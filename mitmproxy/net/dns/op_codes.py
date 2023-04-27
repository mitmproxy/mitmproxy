QUERY = 0
IQUERY = 1
STATUS = 2
NOTIFY = 4
UPDATE = 5
DSO = 6

_STRINGS = {
    QUERY: "QUERY",
    IQUERY: "IQUERY",
    STATUS: "STATUS",
    NOTIFY: "NOTIFY",
    UPDATE: "UPDATE",
    DSO: "DSO",
}


def to_str(op_code: int) -> str:
    return _STRINGS.get(op_code, f"OPCODE({op_code})")
