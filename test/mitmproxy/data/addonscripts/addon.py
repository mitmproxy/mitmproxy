event_log = []


class Addon:
    @property
    def event_log(self):
        return event_log

    def start(self):
        event_log.append("addonstart")

    def configure(self, options):
        event_log.append("addonconfigure")


def configure(options):
    event_log.append("addonconfigure")


def start():
    event_log.append("scriptstart")
    return Addon()
