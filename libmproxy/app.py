import flask
from flask import send_from_directory, jsonify

mapp = flask.Flask(__name__)
mapp.debug = True


@mapp.route("/")
def index():
    return flask.render_template("index.html", section="home")

@mapp.route('/app/')
def indx():
	return app("index.html")

@mapp.route('/app/<path:filename>')
def app(filename):
    return send_from_directory(mapp.root_path + './gui/', filename)

@mapp.route("/certs")
def certs():
    return flask.render_template("certs.html", section="certs")

@mapp.route("/api/config")
def config():
	m = mapp.config["PMASTER"]
	return jsonify(**{
			"proxy-addr": m.server.server_address[0],
			"proxy-port": m.server.server_address[1] 
		})