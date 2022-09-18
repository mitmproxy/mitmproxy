"""Post messages to mitmproxy's event log."""
import logging

from mitmproxy.log import ALERT


def load(l):
    logging.info("This is some informative text.")
    logging.warning("This is a warning.")
    logging.error("This is an error.")
    logging.log(ALERT, "This is an alert. It has the same urgency as info, but will also pop up in the status bar.")
