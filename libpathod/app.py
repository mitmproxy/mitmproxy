import logging
from flask import Flask, jsonify, render_template
import version

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
    return render_template("index.html", name="index", section="main")
    


"""
class _Page(tornado.web.RequestHandler):
    def render(self, name, **kwargs):
        tornado.web.RequestHandler.render(self, name + ".html", **kwargs)


class Index(_Page):
    name = "index"
    section = "main"
    def get(self):
        self.render(self.name, section=self.section, spec="")


class Preview(_Page):
    name = "preview"
    section = "main"
    SANITY = 1024*1024
    def get(self):
        spec = self.get_argument("spec", None)
        args = dict(
            spec = spec,
            section = self.section,
            syntaxerror = None,
            error = None
        )
        try:
            r = rparse.parse(self.application.settings, spec)
        except rparse.ParseException, v:
            args["syntaxerror"] = str(v)
            args["marked"] = v.marked()
            return self.render(self.name, **args)
        if r.length() > self.SANITY:
            error = "Refusing to preview a response of %s bytes. This is for your own good."%r.length()
            args["error"] = error
        else:
            d = utils.DummyRequest()
            r.serve(d)
            args["output"] = d.getvalue()
        self.render(self.name, **args)


class Help(_Page):
    name = "help"
    section = "help"
    def get(self):
        self.render(self.name, section=self.section)


class Log(_Page):
    name = "log"
    section = "log"
    def get(self):
        self.render(self.name, section=self.section, log=self.application.log)


class OneLog(_Page):
    name = "onelog"
    section = "log"
    def get(self, lid):
        l = pprint.pformat(self.application.log_by_id(int(lid)))
        self.render(self.name, section=self.section, alog=l, lid=lid)


class ClearLog(_Page):
    def post(self):
        self.application.clear_logs()
        self.redirect("/log")
"""
