"""Post messages to mitmproxy's event log."""

import logging

from mitmproxy.addonmanager import Loader
from mitmproxy.log import ALERT

logger = logging.getLogger(__name__)


def load(loader: Loader):
    logger.info("This is some informative text.")
    logger.warning("This is a warning.")
    logger.error("This is an error.")
    logger.log(
        ALERT,
        "This is an alert. It has the same urgency as info, but will also pop up in the status bar.",
    )
