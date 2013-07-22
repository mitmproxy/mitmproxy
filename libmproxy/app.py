import flask

mapp = flask.Flask(__name__)
mapp.debug = True


@mapp.route("/")
def index():
    return flask.render_template("index.html", section="home")


@mapp.route("/certs")
def certs():
    return flask.render_template("certs.html", section="certs")
