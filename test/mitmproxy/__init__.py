# Silence third-party modules
import logging
logging.getLogger("hyper").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("passlib").setLevel(logging.WARNING)
logging.getLogger("tornado").setLevel(logging.WARNING)
