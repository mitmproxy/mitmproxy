event_log = []


class Addon:
    @property
    def event_log(self):
        return event_log

    def load(self, opts):
        event_log.append("addonload")

    def configure(self, options, updated):
        event_log.append("addonconfigure")


def configure(options, updated):
    event_log.append("addonconfigure")


def load(opts):
    event_log.append("scriptload")
    return Addon()
