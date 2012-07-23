import logging, pprint, cStringIO
from flask import Flask, jsonify, render_template, request, abort
import version, rparse, utils

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


@app.route('/docs/pathod')
def docs_pathod():
    return render_template("docs_pathod.html", section="docs")


@app.route('/docs/language')
def docs_language():
    return render_template("docs_lang.html", section="docs")


@app.route('/docs/pathoc')
def docs_pathoc():
    return render_template("docs_pathoc.html", section="docs")


@app.route('/docs/test')
def docs_test():
    return render_template("docs_test.html", section="docs")


@app.route('/log')
def log():
    return render_template("log.html", section="log", log=app.config["pathod"].get_log())


@app.route('/log/<int:lid>')
def onelog(lid):
    item = app.config["pathod"].log_by_id(int(lid))
    if not item:
        abort(404)
    l = pprint.pformat(item)
    return render_template("onelog.html", section="log", alog=l, lid=lid)


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

    s = cStringIO.StringIO()
    r.serve(s, check=app.config["pathod"].check_size)
    args["output"] = utils.escape_unprintables(s.getvalue())
    return render_template("preview.html", **args)
