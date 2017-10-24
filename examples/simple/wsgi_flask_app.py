"""
This example shows how to graft a WSGI app onto mitmproxy. In this
instance, we're using the Flask framework (http://flask.pocoo.org/) to expose
a single simplest-possible page.
"""
from flask import Flask
from mitmproxy.addons import wsgiapp

app = Flask("proxapp")


@app.route('/')
def hello_world() -> str:
    return 'Hello World!'


def start():
    # Host app at the magic domain "proxapp.local" on port 80. Requests to this
    # domain and port combination will now be routed to the WSGI app instance.
    return wsgiapp.WSGIApp(app, "proxapp.local", 80)
