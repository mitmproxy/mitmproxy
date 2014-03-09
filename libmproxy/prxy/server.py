__author__ = 'user'


class AddressPriority(object):
    """
    Enum that signifies the priority of the given address when choosing the destination host.
    Higher is better (None < i)
    """
    FORCE = 5
    """forward mode"""
    MANUALLY_CHANGED = 4
    """user changed the target address in the ui"""
    FROM_SETTINGS = 3
    """reverse proxy mode"""
    FROM_CONNECTION = 2
    """derived from transparent resolver"""
    FROM_PROTOCOL = 1
    """derived from protocol (e.g. absolute-form http requests)"""