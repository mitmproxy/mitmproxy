import flask

mapp = flask.Flask(__name__)
mapp.debug = True

def master():
    return flask.request.environ["mitmproxy.master"]

@mapp.route("/")
def index():
    return flask.render_template("index.html", section="home")


@mapp.route("/cert/pem")
def certs_pem():
    p = master().server.config.cacert
    return flask.Response(open(p).read(), mimetype='application/x-x509-ca-cert')


@mapp.route("/cert/p12")
def certs_p12():
    return flask.render_template("certs.html", section="certs")


@mapp.route("/cert/cer")
def certs_cer():
    return flask.render_template("certs.html", section="certs")
