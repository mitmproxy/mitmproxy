import logging, pprint, cStringIO
from flask import Flask, jsonify, render_template, request, abort
import version, rparse, utils

logging.basicConfig(level="DEBUG")
app = Flask(__name__)

def api():
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


def render(s, **kwargs):
    kwargs["noapi"] = app.config["pathod"].noapi
    kwargs["nocraft"] = app.config["pathod"].nocraft
    kwargs["craftanchor"] = app.config["pathod"].craftanchor
    return render_template(s, **kwargs)


@app.route('/')
@app.route('/index.html')
def index():
    return render("index.html", section="main")


@app.route('/docs/pathod')
def docs_pathod():
    return render("docs_pathod.html", section="docs")


@app.route('/docs/language')
def docs_language():
    return render("docs_lang.html", section="docs")


@app.route('/docs/pathoc')
def docs_pathoc():
    return render("docs_pathoc.html", section="docs")


@app.route('/docs/test')
def docs_test():
    return render("docs_test.html", section="docs")


@app.route('/log')
def log():
    if app.config["pathod"].noapi:
        abort(404)
    return render("log.html", section="log", log=app.config["pathod"].get_log())


@app.route('/log/<int:lid>')
def onelog(lid):
    item = app.config["pathod"].log_by_id(int(lid))
    if not item:
        abort(404)
    l = pprint.pformat(item)
    return render("onelog.html", section="log", alog=l, lid=lid)


def _preview(is_request):
    if is_request:
        template = "request_preview.html"
    else:
        template = "response_preview.html"

    spec = request.args["spec"]
    args = dict(
        spec = spec,
        section = "main",
        syntaxerror = None,
        error = None
    )
    try:
        if is_request:
            r = rparse.parse_request(app.config["pathod"].request_settings, spec)
        else:
            r = rparse.parse_response(app.config["pathod"].request_settings, spec)
    except rparse.ParseException, v:
        args["syntaxerror"] = str(v)
        args["marked"] = v.marked()
        return render(template, **args)
    except rparse.FileAccessDenied:
        args["error"] = "File access is disabled."
        return render(template, **args)

    s = cStringIO.StringIO()
    r.preview_safe()

    if is_request:
        r.serve(s, check=app.config["pathod"].check_size, host="example.com")
    else:
        r.serve(s, check=app.config["pathod"].check_size)

    args["output"] = utils.escape_unprintables(s.getvalue())
    return render(template, **args)


@app.route('/response_preview')
def response_preview():
    return _preview(False)
    

@app.route('/request_preview')
def request_preview():
    return _preview(True)

