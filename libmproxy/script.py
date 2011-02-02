"""
    The mitmproxy scripting interface is simple - a serialized representation
    of a flow is passed to the script on stdin, and a possibly modified flow is
    then read by mitmproxy from the scripts stdout. This module provides two
    convenience functions to make loading and returning data from scripts
    simple.
"""
import sys, base64
from contrib import bson
import flow


#begin nocover
def load_flow():
    """
        Load a flow from the stdin. Returns a Flow object.
    """
    data = sys.stdin.read()
    return flow.Flow.script_deserialize(data)


def return_flow(f):
    """
        Print a flow to stdout. 
    """
    print >> sys.stdout, f.script_serialize()
    

