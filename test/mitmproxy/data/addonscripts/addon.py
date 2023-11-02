import logging

event_log = []


class Addon:
    @property
    def event_log(self):
        return event_log

    def load(self, opts):
        logging.info("addon running")
        event_log.append("addonload")

    def configure(self, updated):
        event_log.append("addonconfigure")


def configure(updated):
    event_log.append("scriptconfigure")


def load(loader):
    event_log.append("scriptload")


addons = [Addon()]
