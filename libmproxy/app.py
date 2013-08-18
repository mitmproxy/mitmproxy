import random
import string
import os
import flask
from flask import request, send_from_directory, Response
from flask.json import jsonify, dumps
from flask.helpers import safe_join
from werkzeug.exceptions import *

mapp = flask.Flask(__name__)
mapp.debug = True

xsrf_token = ''.join(
    random.choice(string.ascii_lowercase + string.digits) for _ in range(32))


@mapp.route("/")
def index():
    return flask.render_template("index.html", section="home")


@mapp.route("/certs")
def certs():
    return flask.render_template("certs.html", section="certs")


@mapp.route('/app/')
def appindex():
    return app("index.html")


@mapp.route('/app/<path:filename>')
def app(filename):
    return send_from_directory(mapp.root_path + './gui/', filename)


@mapp.route("/api/config")
def config():
    m = mapp.config["PMASTER"]
    return jsonify(
        proxy=m.server.server_address,
        token=xsrf_token
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


@mapp.route("/api/flows")
def flowlist():
    flows = list(f._get_state() for f in _flow())
    for flow in flows:
        if flow["request"]:
            del flow["request"]["content"]
        if flow["response"]:
            del flow["response"]["content"]
    return Response(dumps(flows), mimetype='application/json')


@mapp.route("/api/flows/<int:flowid>")
def flow(flowid):
    flow = _flow(flowid)._get_state()
    if flow["request"]:
        del flow["request"]["content"]
    if flow["response"]:
        del flow["response"]["content"]
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
    func = getattr(FilesystemApi, request.method)
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
    def POST(path, exists, isfile, isdir):
        if exists:
            raise Conflict()
        json.loads(requestContent)
        dir, file = os.path.split(path)
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(path, "wb") as f:
            f.write(CONTENT)
            #FIXME return 201 created status code
        return jsonify(success=True)
