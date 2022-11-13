from typing import ClassVar


class LayoutWidget:
    """
    All top-level layout widgets and all widgets that may be set in an
    overlay must comply with this API.
    """

    # Title is only required for windows, not overlay components
    title = ""
    keyctx: ClassVar[str] = ""

    def key_responder(self):
        """
        Returns the object responding to key input. Usually self, but may be
        a wrapped object.
        """
        return self

    def focus_changed(self):
        """
        The view focus has changed. Layout objects should implement the API
        rather than directly subscribing to events.
        """

    def view_changed(self):
        """
        The view list has changed.
        """

    def layout_popping(self):
        """
        We are just about to pop a window off the stack, or exit an overlay.
        """

    def layout_pushed(self, prev):
        """
        We have just pushed a window onto the stack.
        """
