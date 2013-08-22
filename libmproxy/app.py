import os
import hashlib
import base64
import flask
import filt
from flask import request, send_from_directory, Response, session
from flask.json import jsonify, dumps
from flask.helpers import safe_join
from werkzeug.exceptions import *
from werkzeug.datastructures import ContentRange
from werkzeug.http import parse_range_header

mapp = flask.Flask(__name__)
mapp.debug = True
mapp.secret_key = os.urandom(32)

def auth_token():
    if mapp.config["auth_token"] is None:
        mapp.config["auth_token"] = base64.b64encode(os.urandom(32))
        print "Auth token:", mapp.config["auth_token"]
    return mapp.config["auth_token"]
xsrf_token = base64.b64encode(os.urandom(32))

@mapp.after_request
def csp_header(response):
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-eval'; style-src 'unsafe-inline' 'self'"
    return response

@mapp.before_request
def auth():
    if session.get("auth", False):
        if request.method == "GET":
            return
        else:
            token = request.headers.get('X-Request-Token', False)
            if token:
                if hashlib.sha1(xsrf_token).hexdigest() == hashlib.sha1(token).hexdigest():
                    return
    else:
        token = request.args.get("auth", False)
        if not auth_token():
            return
        if token:
            if hashlib.sha1(auth_token()).hexdigest() == hashlib.sha1(token).hexdigest():
                session['auth'] = True
                return
    raise Unauthorized()


def require_write_permission(f):
    def wrap(*args, **kwargs):
        if not mapp.config["readonly"]:
            return f(*args, **kwargs)
        raise Unauthorized()
    return wrap


@mapp.route("/")
def index():
    return flask.render_template("index.html", section="home")


@mapp.route("/certs")
def certs():
    return flask.render_template("certs.html", section="certs")


@mapp.route('/app/')
def app():
    return app_static("index.html")


@mapp.route('/app/<path:filename>')
def app_static(filename):
    return send_from_directory(mapp.root_path + './gui/', filename)


@mapp.route("/api/config")
def config():
    m = mapp.config["PMASTER"]
    return jsonify(
        proxy=m.server.server_address,
        token=xsrf_token,
        readonly=mapp.config["readonly"]
    )


def _flow(flowid=None):
    m = mapp.config["PMASTER"]
    try:
        if flowid:
            return m.state._flow_list[flowid]
        else:
            return m.state._flow_list
    except:
        raise BadRequest()


def _parsefilter(filtstr,key=""):
    f = filt.parse(filtstr)
    if not filt:
        raise BadRequest(flask.json.htmlsafe_dumps({ #FIXME check for XSS
            "status": "error",
            "details": "invalid filter %s: %s" % (key, filtstr)
        }))
    return f


def _prepareFlow(flow):
    if flow.get("request", False):
        flow["request"]["contentLength"] = len(flow["request"]["content"])
        del flow["request"]["content"]
    if flow.get("response", False):
        flow["response"]["contentLength"] = len(flow["response"]["content"])
        del flow["response"]["content"]

@mapp.route("/api/flows")
def flowlist():
    flows = _flow()

    # Handle filter
    f = request.args.get("filter", False)
    if f:
        f = _parsefilter(f)
        flows = filter(lambda flow: f(flow), flows)

    # Handle Range Header
    range_str = request.headers.get("Range", False)
    if range_str:
        range_header = parse_range_header(range_str)
        if len(range_header.ranges) != 1:
            raise RequestedRangeNotSatisfiable()
        range_start, range_end = range_header.ranges[0]
    else:
        range_start = 0
        range_end = max(len(flows) - 1, 0)
    flows = flows[range_start:range_end+1]

    # Handle tags
    flows = list((f, f._get_state()) for f in flows)
    for _, state in flows:
        state["tags"] = []
    for k, v in request.args.iteritems():
        if k in ["filter", ]:
            continue
        f = _parsefilter(v, k)
        for flow, state in flows:
            if f(flow):
                state["tags"].append(k)
    flows = map(lambda x: x[1], flows)

    #Prepare flow list (remove content from state etc)
    i = range_start
    for flow in flows:
        flow["id"] = i  # FIXME: Using filters, this leads to shit results (fixing id fixes this)
        i += 1          # TODO: This should get unneccesary asap
        _prepareFlow(flow)

    code = 206 if range_str else 200
    headers = {
        'Content-Type': 'application/json',
        'Content-Range': ContentRange("items", None, None, len(flows)).to_header()
        #Skip start and end parameters to please werkzeugs range validator.
        #api users can only rely on the submitted total count
    }
    return dumps(flows), code, headers


@mapp.route("/api/flows/<int:flowid>")
def flow(flowid):
    flow = _flow(flowid)._get_state()
    flow["id"] = flowid
    _prepareFlow(flow)
    return jsonify(flow)


@mapp.route("/api/flows/<int:flowid>/<message>/content")
def content(flowid, message):
    flow = _flow(flowid)
    try:
        message = getattr(flow, message)
    except:
        raise BadRequest()
    if not hasattr(message, "content"):
        raise UnprocessableEntity()
    return content


@mapp.route("/api/fs/<path:path>", methods=['GET', 'POST', 'PUT', 'DELETE'])
def fsapi(path):
    path = safe_join(mapp.root_path + '/../scripts/gui', path)
    func = getattr(FilesystemApi, str(request.method))
    return func(
        path=path,
        exists=os.path.exists(path),
        isfile=os.path.isfile(path),
        isdir=os.path.isdir(path)
    )


@mapp.route("/api/fs/")
def fsapi_index():
    return fsapi("")


class FilesystemApi:
    @staticmethod
    def GET(path, exists, isfile, isdir):
        if not exists:
            raise NotFound()
        if isfile:
            with open(path, "rb") as f:
                content = f.read()
            return content
        if isdir:
            is_recursive = request.args.get('recursive', False)
            ret = []
            if is_recursive:
                for dirpath, dirnames, filenames in os.walk(path):
                    ret.append((dirpath[len(path):], dirnames, filenames))
            else:
                files = []
                dirs = []
                for i in os.listdir(path):
                    if os.path.isfile(os.path.join(path, i)):
                        files.append(i)
                    else:
                        dirs.append(i)
                ret = ("", dirs, files)
            return Response(dumps(ret), mimetype='application/json')
        raise InternalServerError()

    @staticmethod
    @require_write_permission
    def POST(path, exists, isfile, isdir):
        if exists:
            raise Conflict()
        directory, filename = os.path.split(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, "wb") as f:
            f.write(request.data)
        return jsonify(success=True), 201

    @staticmethod
    @require_write_permission
    def PUT(path, exists, isfile, isdir):
        if not exists:
            raise Conflict()
        with open(path, "wb") as f:
            f.write(request.data)
        return jsonify(success=True)

    @staticmethod
    @require_write_permission
    def DELETE(path, exists, isfile, isdir):
        if not exists:
            raise NotFound()
        if isfile:
            os.remove(path)
            return jsonify(success=True)
        if isdir:
            os.rmdir(path)
            return jsonify(success=True)
        raise InternalServerError()
