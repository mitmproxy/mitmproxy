from ctypes import Structure, Union, windll, POINTER
from ctypes.wintypes import BOOL, DWORD, WCHAR, WORD, SHORT, UINT, HANDLE, LPDWORD, CHAR

# https://docs.microsoft.com/de-de/windows/console/getstdhandle
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11

# https://docs.microsoft.com/de-de/windows/console/setconsolemode
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
DISABLE_NEWLINE_AUTO_RETURN = 0x0008
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
ENABLE_WINDOW_INPUT = 0x0008


class COORD(Structure):
    """https://docs.microsoft.com/en-us/windows/console/coord-str"""

    _fields_ = [
        ("X", SHORT),
        ("Y", SHORT),
    ]


class SMALL_RECT(Structure):
    """https://docs.microsoft.com/en-us/windows/console/small-rect-str"""

    _fields_ = [
        ("Left", SHORT),
        ("Top", SHORT),
        ("Right", SHORT),
        ("Bottom", SHORT),
    ]


class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    """https://docs.microsoft.com/en-us/windows/console/console-screen-buffer-info-str"""

    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", WORD),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]


class uChar(Union):
    """https://docs.microsoft.com/en-us/windows/console/key-event-record-str"""
    _fields_ = [
        ("AsciiChar", CHAR),
        ("UnicodeChar", WCHAR),
    ]


class KEY_EVENT_RECORD(Structure):
    """https://docs.microsoft.com/en-us/windows/console/key-event-record-str"""

    _fields_ = [
        ("bKeyDown", BOOL),
        ("wRepeatCount", WORD),
        ("wVirtualKeyCode", WORD),
        ("wVirtualScanCode", WORD),
        ("uChar", uChar),
        ("dwControlKeyState", DWORD),
    ]


class MOUSE_EVENT_RECORD(Structure):
    """https://docs.microsoft.com/en-us/windows/console/mouse-event-record-str"""

    _fields_ = [
        ("dwMousePosition", COORD),
        ("dwButtonState", DWORD),
        ("dwControlKeyState", DWORD),
        ("dwEventFlags", DWORD),
    ]


class WINDOW_BUFFER_SIZE_RECORD(Structure):
    """https://docs.microsoft.com/en-us/windows/console/window-buffer-size-record-str"""

    _fields_ = [("dwSize", COORD)]


class MENU_EVENT_RECORD(Structure):
    """https://docs.microsoft.com/en-us/windows/console/menu-event-record-str"""

    _fields_ = [("dwCommandId", UINT)]


class FOCUS_EVENT_RECORD(Structure):
    """https://docs.microsoft.com/en-us/windows/console/focus-event-record-str"""

    _fields_ = [("bSetFocus", BOOL)]


class Event(Union):
    """https://docs.microsoft.com/en-us/windows/console/input-record-str"""
    _fields_ = [
        ("KeyEvent", KEY_EVENT_RECORD),
        ("MouseEvent", MOUSE_EVENT_RECORD),
        ("WindowBufferSizeEvent", WINDOW_BUFFER_SIZE_RECORD),
        ("MenuEvent", MENU_EVENT_RECORD),
        ("FocusEvent", FOCUS_EVENT_RECORD),
    ]


class INPUT_RECORD(Structure):
    """https://docs.microsoft.com/en-us/windows/console/input-record-str"""

    _fields_ = [
        ("EventType", WORD),
        ("Event", Event)
    ]


class EventType:
    FOCUS_EVENT = 0x0010
    KEY_EVENT = 0x0001
    MENU_EVENT = 0x0008
    MOUSE_EVENT = 0x0002
    WINDOW_BUFFER_SIZE_EVENT = 0x0004


# https://docs.microsoft.com/de-de/windows/console/getstdhandle
GetStdHandle = windll.kernel32.GetStdHandle
GetStdHandle.argtypes = [DWORD]
GetStdHandle.restype = HANDLE

# https://docs.microsoft.com/de-de/windows/console/getconsolemode
GetConsoleMode = windll.kernel32.GetConsoleMode
GetConsoleMode.argtypes = [HANDLE, LPDWORD]
GetConsoleMode.restype = BOOL

# https://docs.microsoft.com/de-de/windows/console/setconsolemode
SetConsoleMode = windll.kernel32.SetConsoleMode
SetConsoleMode.argtypes = [HANDLE, DWORD]
SetConsoleMode.restype = BOOL

# https://docs.microsoft.com/de-de/windows/console/readconsoleinput
ReadConsoleInputW = windll.kernel32.ReadConsoleInputW
# ReadConsoleInputW.argtypes = [HANDLE, POINTER(INPUT_RECORD), DWORD, LPDWORD]
ReadConsoleInputW.restype = BOOL

# https://docs.microsoft.com/en-us/windows/console/getconsolescreenbufferinfo
GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
GetConsoleScreenBufferInfo.argtypes = [HANDLE, POINTER(CONSOLE_SCREEN_BUFFER_INFO)]
GetConsoleScreenBufferInfo.restype = BOOL
