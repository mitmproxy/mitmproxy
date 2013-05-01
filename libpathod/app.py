import logging, pprint, cStringIO
from flask import Flask, jsonify, render_template, request, abort, make_response
import version, language, utils
from netlib import http_uastrings

logging.basicConfig(level="DEBUG")
def make_app(noapi):
    app = Flask(__name__)

    if not noapi:
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


    def render(s, cacheable, **kwargs):
        kwargs["noapi"] = app.config["pathod"].noapi
        kwargs["nocraft"] = app.config["pathod"].nocraft
        kwargs["craftanchor"] = app.config["pathod"].craftanchor
        resp = make_response(render_template(s, **kwargs), 200)
        if cacheable:
            resp.headers["Cache-control"] = "public, max-age=4320"
        return resp


    @app.route('/')
    @app.route('/index.html')
    def index():
        return render("index.html", True, section="main")


    @app.route('/download')
    @app.route('/download.html')
    def download():
        return render("download.html", True, section="download", version=version.VERSION)


    @app.route('/about')
    @app.route('/about.html')
    def about():
        return render("about.html", True, section="about")


    @app.route('/docs/pathod')
    def docs_pathod():
        return render("docs_pathod.html", True, section="docs", subsection="pathod")


    @app.route('/docs/language')
    def docs_language():
        return render(
            "docs_lang.html", True,
            section="docs", uastrings=http_uastrings.UASTRINGS,
            subsection="lang"
        )


    @app.route('/docs/pathoc')
    def docs_pathoc():
        return render("docs_pathoc.html", True, section="docs", subsection="pathoc")


    @app.route('/docs/libpathod')
    def docs_libpathod():
        return render("docs_libpathod.html", True, section="docs", subsection="libpathod")


    @app.route('/docs/test')
    def docs_test():
        return render("docs_test.html", True, section="docs", subsection="test")


    @app.route('/log')
    def log():
        if app.config["pathod"].noapi:
            abort(404)
        return render("log.html", False, section="log", log=app.config["pathod"].get_log())


    @app.route('/log/<int:lid>')
    def onelog(lid):
        item = app.config["pathod"].log_by_id(int(lid))
        if not item:
            abort(404)
        l = pprint.pformat(item)
        return render("onelog.html", False, section="log", alog=l, lid=lid)


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
            error = None,
        )
        if not spec.strip():
            args["error"] = "Can't parse an empty spec."
            return render(template, False, **args)

        try:
            if is_request:
                r = language.parse_request(app.config["pathod"].request_settings, spec)
            else:
                r = language.parse_response(app.config["pathod"].request_settings, spec)
        except language.ParseException, v:
            args["syntaxerror"] = str(v)
            args["marked"] = v.marked()
            return render(template, False, **args)

        s = cStringIO.StringIO()
        safe = r.preview_safe()

        c = app.config["pathod"].check_policy(safe, app.config["pathod"].request_settings)
        if c:
            args["error"] = c
            return render(template, False, **args)
        if is_request:
            language.serve(safe, s, app.config["pathod"].request_settings, "example.com")
        else:
            language.serve(safe, s, app.config["pathod"].request_settings, None)

        args["output"] = utils.escape_unprintables(s.getvalue())
        return render(template, False, **args)


    @app.route('/response_preview')
    def response_preview():
        return _preview(False)


    @app.route('/request_preview')
    def request_preview():
        return _preview(True)
    return app

