import typing

from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.http import HTTPFlow, HTTPResponse, HTTPRequest
from mitmproxy.certs import Cert
from mitmproxy.connections import ClientConnection, ServerConnection
from mitmproxy.io.proto import http_pb2


def _move_attrs(s_obj, d_obj, attrs):
    for attr in attrs:
        if not isinstance(d_obj, dict):
            if hasattr(s_obj, attr) and getattr(s_obj, attr) is not None:
                setattr(d_obj, attr, getattr(s_obj, attr))
        else:
            if hasattr(s_obj, attr) and getattr(s_obj, attr) is not None:
                # ugly fix to set None in empty str or bytes fields
                if getattr(s_obj, attr) == "" or getattr(s_obj, attr) == b"":
                    d_obj[attr] = None
                else:
                    d_obj[attr] = getattr(s_obj, attr)


def _dump_http_response(res: HTTPResponse) -> http_pb2.HTTPResponse:
    pres = http_pb2.HTTPResponse()
    _move_attrs(res, pres, ['http_version', 'status_code', 'reason',
                            'content', 'timestamp_start', 'timestamp_end', 'is_replay'])
    if res.headers:
        for h in res.headers.fields:
            header = pres.headers.add()
            header.name = h[0]
            header.value = h[1]
    return pres


def _dump_http_request(req: HTTPRequest) -> http_pb2.HTTPRequest:
    preq = http_pb2.HTTPRequest()
    _move_attrs(req, preq, ['first_line_format', 'method', 'scheme', 'host', 'port', 'path', 'http_version', 'content',
                            'timestamp_start', 'timestamp_end', 'is_replay'])
    if req.headers:
        for h in req.headers.fields:
            header = preq.headers.add()
            header.name = h[0]
            header.value = h[1]
    return preq


def _dump_http_client_conn(cc: ClientConnection) -> http_pb2.ClientConnection:
    pcc = http_pb2.ClientConnection()
    _move_attrs(cc, pcc, ['id', 'tls_established', 'timestamp_start', 'timestamp_tls_setup', 'timestamp_end', 'sni',
                          'cipher_name', 'alpn_proto_negotiated', 'tls_version'])
    for cert in ['clientcert', 'mitmcert']:
        if hasattr(cc, cert) and getattr(cc, cert) is not None:
            setattr(pcc, cert, getattr(cc, cert).to_pem())
    if cc.tls_extensions:
        for extension in cc.tls_extensions:
            ext = pcc.tls_extensions.add()
            ext.int = extension[0]
            ext.bytes = extension[1]
    if cc.address:
        pcc.address.host = cc.address[0]
        pcc.address.port = cc.address[1]
    return pcc


def _dump_http_server_conn(sc: ServerConnection) -> http_pb2.ServerConnection:
    psc = http_pb2.ServerConnection()
    _move_attrs(sc, psc, ['id', 'tls_established', 'sni', 'alpn_proto_negotiated', 'tls_version',
                          'timestamp_start', 'timestamp_tcp_setup', 'timestamp_tls_setup', 'timestamp_end'])
    for addr in ['address', 'ip_address', 'source_address']:
        if hasattr(sc, addr) and getattr(sc, addr) is not None:
            getattr(psc, addr).host = getattr(sc, addr)[0]
            getattr(psc, addr).port = getattr(sc, addr)[1]
    if sc.cert:
        psc.cert = sc.cert.to_pem()
    if sc.via:
        psc.via.MergeFrom(_dump_http_server_conn(sc.via))
    return psc


def _dump_http_error(e: flow.Error) -> http_pb2.HTTPError:
    pe = http_pb2.HTTPError()
    for attr in ['msg', 'timestamp']:
        if hasattr(e, attr) and getattr(e, attr) is not None:
            setattr(pe, attr, getattr(e, attr))
    return pe


def dump_http(f: flow.Flow) -> http_pb2.HTTPFlow:
    pf = http_pb2.HTTPFlow()
    for p in ['request', 'response', 'client_conn', 'server_conn', 'error']:
        if hasattr(f, p) and getattr(f, p):
            getattr(pf, p).MergeFrom(eval(f"_dump_http_{p}")(getattr(f, p)))
    _move_attrs(f, pf, ['intercepted', 'marked', 'mode', 'id'])
    return pf


def dumps(f: flow.Flow) -> bytes:
    if f.type != "http":
        raise exceptions.TypeError("Flow types different than HTTP not supported yet!")
    else:
        p = dump_http(f)
        return p.SerializeToString()


def _load_http_request(o: http_pb2.HTTPRequest) -> HTTPRequest:
    d: dict = {}
    _move_attrs(o, d, ['first_line_format', 'method', 'scheme', 'host', 'port', 'path', 'http_version', 'content',
                       'timestamp_start', 'timestamp_end', 'is_replay'])
    if d['content'] is None:
        d['content'] = b""
    d["headers"] = []
    for header in o.headers:
        d["headers"].append((bytes(header.name, "utf-8"), bytes(header.value, "utf-8")))

    return HTTPRequest(**d)


def _load_http_response(o: http_pb2.HTTPResponse) -> HTTPResponse:
    d: dict = {}
    _move_attrs(o, d, ['http_version', 'status_code', 'reason',
                       'content', 'timestamp_start', 'timestamp_end', 'is_replay'])
    if d['content'] is None:
        d['content'] = b""
    d["headers"] = []
    for header in o.headers:
        d["headers"].append((bytes(header.name, "utf-8"), bytes(header.value, "utf-8")))

    return HTTPResponse(**d)


def _load_http_client_conn(o: http_pb2.ClientConnection) -> ClientConnection:
    d: dict = {}
    _move_attrs(o, d, ['id', 'tls_established', 'sni', 'cipher_name', 'alpn_proto_negotiated', 'tls_version',
                       'timestamp_start', 'timestamp_tcp_setup', 'timestamp_tls_setup', 'timestamp_end'])
    for cert in ['clientcert', 'mitmcert']:
        if hasattr(o, cert) and getattr(o, cert):
            d[cert] = Cert.from_pem(getattr(o, cert))
    if o.tls_extensions:
        d['tls_extensions'] = []
        for extension in o.tls_extensions:
            d['tls_extensions'].append((extension.int, extension.bytes))
    if o.address:
        d['address'] = (o.address.host, o.address.port)
    cc = ClientConnection(None, tuple(), None)
    for k, v in d.items():
        setattr(cc, k, v)
    return cc


def _load_http_server_conn(o: http_pb2.ServerConnection) -> ServerConnection:
    d: dict = {}
    _move_attrs(o, d, ['id', 'tls_established', 'sni', 'alpn_proto_negotiated', 'tls_version',
                       'timestamp_start', 'timestamp_tcp_setup', 'timestamp_tls_setup', 'timestamp_end'])
    for addr in ['address', 'ip_address', 'source_address']:
        if hasattr(o, addr):
            d[addr] = (getattr(o, addr).host, getattr(o, addr).port)
    if o.cert:
        c = Cert.from_pem(o.cert)
        d['cert'] = c
    if o.HasField('via'):
        d['via'] = _load_http_server_conn(o.via)
    sc = ServerConnection(tuple())
    for k, v in d.items():
        setattr(sc, k, v)
    return sc


def _load_http_error(o: http_pb2.HTTPError) -> typing.Optional[flow.Error]:
    d = {}
    for m in ['msg', 'timestamp']:
        if hasattr(o, m) and getattr(o, m):
            d[m] = getattr(o, m)
    return None if not d else flow.Error(**d)


def load_http(hf: http_pb2.HTTPFlow) -> HTTPFlow:
    parts = {}
    for p in ['request', 'response', 'client_conn', 'server_conn', 'error']:
        if hf.HasField(p):
            parts[p] = eval(f"_load_http_{p}")(getattr(hf, p))
        else:
            parts[p] = None
    _move_attrs(hf, parts, ['intercepted', 'marked', 'mode', 'id'])
    f = HTTPFlow(ClientConnection(None, tuple(), None), ServerConnection(tuple()))
    for k, v in parts.items():
        setattr(f, k, v)
    return f


def loads(b: bytes, typ="http") -> typing.Union[HTTPFlow]:
    if typ != 'http':
        raise exceptions.TypeError("Flow types different than HTTP not supported yet!")
    else:
        p = http_pb2.HTTPFlow()
        p.ParseFromString(b)
        return load_http(p)
