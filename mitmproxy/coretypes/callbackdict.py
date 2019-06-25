
class CallbackDict(dict):
    """
        Definition of a dictionary which call a function when it is updated.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = None

    def __setitem__(self, key, value):
        res = dict.__setitem__(self, key, value)
        if self.callback:
            self.callback()
        return res

    def __delitem__(self, key):
        res = dict.__delitem__(self, key)
        if self.callback:
            self.callback()
        return res
