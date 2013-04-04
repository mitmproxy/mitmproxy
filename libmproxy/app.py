import flask

mapp = flask.Flask(__name__)

@mapp.route("/")
def hello():
    return "mitmproxy"
