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

steps = [
    "overview",
    "user_interface",
    "intercept_requests",
    "modify_requests",
    "replay_requests",
    "whats_next"
]

@app.route('/')
def index():
    return redirect("/mitmproxy")

@app.route('/<tool>/', defaults={"step": None})
@app.route('/<tool>/<step>')
def mitmproxy(tool, step):
    if not step or step not in steps:
        step = steps[0]

    return render_template(
        tool + "/steps/" + step + ".html",
        tool=tool,
        votes=votes,
        step=step
    )

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
