from __future__ import (print_function, absolute_import, division)

# Silence third-party modules
import logging
logging.getLogger("hyper").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("passlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("tornado").setLevel(logging.WARNING)
