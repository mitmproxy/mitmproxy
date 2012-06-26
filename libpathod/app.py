import logging, pprint, cStringIO
from flask import Flask, jsonify, render_template, request
import version, rparse

logging.basicConfig(level="DEBUG")
app = Flask(__name__)

@app.route('/api/info')
def api_info():
    return jsonify(
        version = version.IVERSION
    )


@app.route('/api/log')
def api_log():
    return jsonify(
        log = app.config["pathod"].get_log()
    )


@app.route('/api/clear_log')
def api_clear_log():
    app.config["pathod"].clear_log()
    return "OK"


@app.route('/')
@app.route('/index.html')
def index():
    return render_template("index.html", section="main")


@app.route('/help')
def help():
    return render_template("help.html", section="help")


@app.route('/log')
def log():
    return render_template("log.html", section="log", log=app.config["pathod"].get_log())


@app.route('/log/<int:lid>')
def onelog(lid):
    l = pprint.pformat(app.config["pathod"].log_by_id(int(lid)))
    return render_template("onelog.html", section="log", alog=l, lid=lid)


SANITY = 1024*1024
@app.route('/preview')
def preview():
    spec = request.args["spec"]
    args = dict(
        spec = spec,
        section = "main",
        syntaxerror = None,
        error = None
    )
    try:
        r = rparse.parse_response(app.config["pathod"].request_settings, spec)
    except rparse.ParseException, v:
        args["syntaxerror"] = str(v)
        args["marked"] = v.marked()
        return render_template("preview.html", **args)
    if r.length() > SANITY:
        error = "Refusing to preview a response of %s bytes. This is for your own good."%r.length()
        args["error"] = error
    else:
        s = cStringIO.StringIO()
        r.serve(s)
        args["output"] = s.getvalue()
    return render_template("preview.html", **args)
