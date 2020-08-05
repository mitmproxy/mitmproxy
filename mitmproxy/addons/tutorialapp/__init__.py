import os

from flask import Flask, render_template, redirect

from mitmproxy.options import CONF_BASENAME, CONF_DIR

app = Flask(__name__)
# will be overridden in the addon, setting this here so that the Flask app can be run standalone.
app.config["CONFDIR"] = CONF_DIR
app.config['TEMPLATES_AUTO_RELOAD'] = True

votes = {
    "cat": 0,
    "dog": 0
}

@app.route('/')
def index():
    return redirect("/mitmproxy")


@app.route('/mitmproxy')
def mitmproxy():
    return render_template("mitmproxy/index.html", votes=votes)


@app.route('/mitmweb')
def mitmweb():
    return render_template("mitmweb/index.html", votes=votes)

@app.route('/votes')
def get_votes():
    return votes


@app.route('/vote/<party>')
def vote(party):
    votes[party] += 1
    return votes


@app.route('/reset_votes')
def reset_votes():
    votes["cat"] = 0
    votes["dog"] = 0
    return votes
