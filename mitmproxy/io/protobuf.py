from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.http import HTTPFlow, HTTPResponse, HTTPRequest
from mitmproxy.connections import ClientConnection, ServerConnection
from mitmproxy.io.proto import http_pb2


def _parse_attr(s_obj, d_obj, attrs):
    for attr in attrs:
        if hasattr(s_obj, attr) and getattr(s_obj, attr) is not None:
            setattr(d_obj, attr, getattr(s_obj, attr))


def _parse_http_response(res: HTTPResponse) -> http_pb2.HTTPResponse:
    pres = http_pb2.HTTPResponse()
    _parse_attr(res, pres, ['http_version', 'status_code', 'reason',
                            'content', 'timestamp_start', 'timestamp_end', 'is_replay'])
    if res.headers:
        for h in res.headers.fields:
            header = pres.headers.add()
            header.name = h[0]
            header.value = h[1]
    return pres


def _parse_http_request(req: HTTPRequest) -> http_pb2.HTTPRequest:
    preq = http_pb2.HTTPRequest()
    _parse_attr(req, preq, ['first_line_format', 'method', 'scheme', 'host', 'port', 'path', 'http_version', 'content',
                            'timestamp_start', 'timestamp_end', 'is_replay'])
    if req.headers:
        for h in req.headers.fields:
            header = preq.headers.add()
            header.name = h[0]
            header.value = h[1]
    return preq


def _parse_http_client(cc: ClientConnection) -> http_pb2.ClientConnection:
    pcc = http_pb2.ClientConnection()
    _parse_attr(cc, pcc, ['id', 'tls_established', 'timestamp_start', 'timestamp_tls_setup', 'timestamp_end', 'sni',
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


def _parse_http_server(sc: ServerConnection) -> http_pb2.ServerConnection:
    psc = http_pb2.ServerConnection()
    _parse_attr(sc, psc, ['id', 'tls_established', 'sni', 'alpn_proto_negotiated', 'tls_version',
                          'timestamp_start', 'timestamp_tcp_setup', 'timestamp_tls_setup', 'timestamp_end'])
    for addr in ['address', 'ip_address', 'source_address']:
        if hasattr(sc, addr) and getattr(sc, addr) is not None:
            getattr(psc, addr).host = getattr(sc, addr)[0]
            getattr(psc, addr).port = getattr(sc, addr)[1]
    if psc.cert:
        psc.cert = sc.cert.to_pem()
    if sc.via:
        psc.via.MergeFrom(_parse_http_server(sc.via))
    return psc


def _parse_http_error(e: flow.Error) -> http_pb2.HTTPError:
    pe = http_pb2.HTTPError()
    for attr in ['msg', 'timestamp']:
        if hasattr(e, attr) and getattr(e, attr) is not None:
            setattr(pe, attr, getattr(e, attr))
    return pe


def _parse_http(f: HTTPFlow) -> http_pb2.HTTPFlow():
    pf = http_pb2.HTTPFlow()
    if f.request:
        pf.request.MergeFrom(_parse_http_request(f.request))
    if f.response:
        pf.response.MergeFrom(_parse_http_response(f.response))
    if f.client_conn:
        pf.client_conn.MergeFrom(_parse_http_client(f.client_conn))
    if f.server_conn:
        pf.server_conn.MergeFrom(_parse_http_server(f.server_conn))
    if f.error:
        pf.error.MergeFrom(_parse_http_error(f.error))
    _parse_attr(f, pf, ['intercepted', 'marked', 'mode', 'id', 'version'])
    return pf


def dumps(f: flow.Flow) -> bytes:
    if f.type != "http":
        raise exceptions.TypeError("Flow types different than HTTP not supported yet!")
    else:
        p = _parse_http(f)
        return p.SerializeToString()


def dumps_state(f: flow.Flow) -> bytes:
    if f.type != "http":
        raise exceptions.TypeError("Flow types different than HTTP not supported yet!")
    else:
        hf = http_pb2.HTTPFlow()
        state = f.get_state()
        for r in ['request', 'response']:
            for field in state[r]:
                if hasattr(getattr(hf, r), field) and state[r][field] is not None:
                    if field == 'headers':
                        for n, v in state[r][field]:
                            header = (getattr(hf, r)).headers.add()
                            header.name = n
                            header.value = v
                    else:
                        setattr(getattr(hf, r), field, state[r][field])
        if state['error']:
            hf.error.msg = state['error']['msg']
            hf.error.timestamp = state['error']['timestamp']
        for c in ['client_conn', 'server_conn']:
            for field in state[c]:
                if hasattr(getattr(hf, c), field) and state[c][field] is not None:
                    if field in ['address', 'ip_address', 'source_address']:
                        getattr(getattr(hf, c), field).host = state[c][field][0]
                        getattr(getattr(hf, c), field).port = state[c][field][1]
                    elif field == "tls_extensions":
                        for t in state[c][field]:
                            if t[0] and t[1]:
                                ext = getattr(hf, c).tls_extensions.add()
                                ext.int = t[0]
                                ext.bytes = t[1]
                    else:
                        setattr(getattr(hf, c), field, state[c][field])
        for val in ['intercepted', 'marked', 'mode', 'id', 'version']:
            if state[val] is not None:
                setattr(hf, val, state[val])
    return hf.SerializeToString()


def loads_state(blob: bytes) -> flow.Flow:
    r = http_pb2.HTTPFlow()
    state = dict()
    r.ParseFromString(blob)
    _dump_object(r, state)
    # ugly repair for tls_extensions typing
    for c in ["client_conn", "server_conn"]:
        state[c]['tls_extensions'] = []
    return HTTPFlow.from_state(state)


def _dump_object(obj, d):
    for descriptor in obj.DESCRIPTOR.fields:
        value = getattr(obj, descriptor.name)
        if descriptor.type == descriptor.TYPE_MESSAGE:
            if descriptor.label == descriptor.LABEL_REPEATED:
                d[descriptor] = []
                if value:
                    for v in value:
                        _dump_object(v, d[descriptor.name])
                else:
                    d[descriptor.name] = None
            else:
                d[descriptor] = {}
                _dump_object(value, d[descriptor.name])
        elif descriptor.type == descriptor.TYPE_ENUM:
            enum_name = descriptor.enum_type.values[value].name
            d[descriptor.name] = enum_name
        else:
            if value == "" or value == b"":
                d[descriptor.name] = None
            else:
                if type(d) == list:
                    d.append([descriptor.name, value])
                elif type(d) == dict:
                    d[descriptor.name] = value
