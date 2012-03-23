import urwid
import common
from .. import utils, encoding

VIEW_CUTOFF = 1024*100

VIEW_CONTENT_RAW = 0
VIEW_CONTENT_HEX = 1
VIEW_CONTENT_PRETTY = 2

CONTENT_VIEWS = {
    VIEW_CONTENT_RAW: "raw",
    VIEW_CONTENT_HEX: "hex",
    VIEW_CONTENT_PRETTY: "pretty"
}

VIEW_CONTENT_PRETTY_TYPE_AUTO = 0
VIEW_CONTENT_PRETTY_TYPE_JSON = 1
VIEW_CONTENT_PRETTY_TYPE_XML = 2
VIEW_CONTENT_PRETTY_TYPE_URLENCODED = 3

CONTENT_PRETTY_NAMES = {
    VIEW_CONTENT_PRETTY_TYPE_JSON: "json",
    VIEW_CONTENT_PRETTY_TYPE_XML: "xmlish",
    VIEW_CONTENT_PRETTY_TYPE_URLENCODED: "urlencoded"
}

CONTENT_PRETTY_TYPES = {
    "text/html": VIEW_CONTENT_PRETTY_TYPE_XML,
    "application/json": VIEW_CONTENT_PRETTY_TYPE_JSON,
    "text/xml": VIEW_CONTENT_PRETTY_TYPE_XML,
    "multipart/form-data": VIEW_CONTENT_PRETTY_TYPE_URLENCODED
}


def trailer(clen, txt):
    rem = clen - VIEW_CUTOFF
    if rem > 0:
        txt.append(urwid.Text(""))
        txt.append(
            urwid.Text(
                [
                    ("highlight", "... %s of data not shown"%utils.pretty_size(rem))
                ]
            )
        )

def view_flow_raw(content):
    txt = []
    for i in utils.cleanBin(content[:VIEW_CUTOFF]).splitlines():
        txt.append(
            urwid.Text(("text", i))
        )
    trailer(len(content), txt)
    return txt

def view_flow_binary(content):
    txt = []
    for offset, hexa, s in utils.hexdump(content[:VIEW_CUTOFF]):
        txt.append(urwid.Text([
            ("offset", offset),
            " ",
            ("text", hexa),
            "   ",
            ("text", s),
        ]))
    trailer(len(content), txt)
    return txt

def view_flow_xmlish(content):
    txt = []
    for i in utils.pretty_xmlish(content[:VIEW_CUTOFF]):
        txt.append(
            urwid.Text(("text", i)),
        )
    trailer(len(content), txt)
    return txt

def view_flow_json(lines):
    txt = []
    sofar = 0
    for i in lines:
        sofar += len(i)
        txt.append(
            urwid.Text(("text", i)),
        )
        if sofar > VIEW_CUTOFF:
            break
    trailer(sum(len(i) for i in lines), txt)
    return txt

def view_flow_formdata(content, boundary):
    rx = re.compile(r'\bname="([^"]+)"')
    keys = []
    vals = []

    for i in content.split("--" + boundary):
        parts = i.splitlines()
        if len(parts) > 1 and parts[0][0:2] != "--":
            match = rx.search(parts[1])
            if match:
                keys.append(match.group(1) + ":")
                vals.append(utils.cleanBin(
                    "\n".join(parts[3+parts[2:].index(""):])
                ))
    r = [
        urwid.Text(("highlight", "Form data:\n")),
    ]
    r.extend(common.format_keyvals(
        zip(keys, vals),
        key = "header",
        val = "text"
    ))
    return r

def view_flow_urlencoded(lines):
    return common.format_keyvals(
                [(k+":", v) for (k, v) in lines],
                key = "header",
                val = "text"
           )

def find_pretty_view(content, hdrItems, pretty_type=VIEW_CONTENT_PRETTY_TYPE_AUTO):
    ctype = None
    if pretty_type == VIEW_CONTENT_PRETTY_TYPE_AUTO:
        pretty_type == None
        for i in hdrItems:
            if i[0].lower() == "content-type":
                ctype = i[1]
                break
        ct = utils.parse_content_type(ctype) if ctype else None
        if ct:
            pretty_type = CONTENT_PRETTY_TYPES.get("%s/%s"%(ct[0], ct[1]))
        if not pretty_type and utils.isXML(content):
            pretty_type = VIEW_CONTENT_PRETTY_TYPE_XML

    if pretty_type == VIEW_CONTENT_PRETTY_TYPE_URLENCODED:
        data = utils.urldecode(content)
        if data:
            return "URLEncoded form", view_flow_urlencoded(data)

    if pretty_type == VIEW_CONTENT_PRETTY_TYPE_XML:
        return "Indented XML-ish", view_flow_xmlish(content)

    if pretty_type == VIEW_CONTENT_PRETTY_TYPE_JSON:
        lines = utils.pretty_json(content)
        if lines:
            return "JSON", view_flow_json(lines)

    return "Falling back to raw.", view_flow_raw(content)


def get_content_view(viewmode, pretty_type, enc, content, hdrItems): 
    """
        Returns a (msg, body) tuple.
    """
    msg = ""
    if viewmode == VIEW_CONTENT_HEX:
        body = view_flow_binary(content)
    elif viewmode == VIEW_CONTENT_PRETTY:
        emsg = ""
        if enc:
            decoded = encoding.decode(enc, content)
            if decoded:
                content = decoded
                if enc and enc != "identity":
                    emsg = "[decoded %s]"%enc
        msg, body = find_pretty_view(content, hdrItems, pretty_type)
        if pretty_type != VIEW_CONTENT_PRETTY_TYPE_AUTO:
            emsg += " (forced to %s)"%(CONTENT_PRETTY_NAMES[pretty_type])
        if emsg:
            msg = emsg + " " + msg
    else:
        body = view_flow_raw(content)
    return msg, body


