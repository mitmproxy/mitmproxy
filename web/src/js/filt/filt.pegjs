// PEG.js filter rules - see http://pegjs.majda.cz/online

{
function or(first, second) {
    // Add explicit function names to ease debugging.
    return function orFilter() {
        first.apply(this, arguments) || second.apply(this, arguments);
    };
}
function and(first, second) {
    return function andFilter() {
        return first.apply(this, arguments) && second.apply(this, arguments);
    }
}
function not(expr) {
    return function notFilter() {
        return !expr.apply(this, arguments);
    };
}
function binding(expr) {
    return function bindingFilter() {
        return expr.apply(this, arguments);
    };
}
function trueFilter(flow) {
    return true;
}
function falseFilter(flow) {
    return false;
}
var ASSET_TYPES = [
    new RegExp("text/javascript"),
    new RegExp("application/x-javascript"),
    new RegExp("application/javascript"),
    new RegExp("text/css"),
    new RegExp("image/.*"),
    new RegExp("application/x-shockwave-flash")
];
function assetFilter(flow) {
    if (flow.response) {
        var ct = ResponseUtils.getContentType(flow.response);
        var i = ASSET_TYPES.length;
        while (i--) {
            if (ASSET_TYPES[i].test(ct)) {
                return true;
            }
        }
    }
    return false;
}
function responseCode(code){
    code = parseInt(code);
    return function responseCodeFilter(flow){
        return flow.response && flow.response.code === code;
    };
}
function domain(regex){
    regex = new RegExp(regex, "i");
    return function domainFilter(flow){
        return flow.request && regex.test(flow.request.host);
    };
}
function errorFilter(flow){
    return !!flow.error;
}
function header(regex){
    regex = new RegExp(regex, "i");
    return function headerFilter(flow){
        return (
            (flow.request && RequestUtils.match_header(flow.request, regex))
            ||
            (flow.response && ResponseUtils.match_header(flow.response, regex))
        );
    };
}
function requestHeader(regex){
    regex = new RegExp(regex, "i");
    return function requestHeaderFilter(flow){
        return (flow.request && RequestUtils.match_header(flow.request, regex));
    }
}
function responseHeader(regex){
    regex = new RegExp(regex, "i");
    return function responseHeaderFilter(flow){
        return (flow.response && ResponseUtils.match_header(flow.response, regex));
    }
}
function method(regex){
    regex = new RegExp(regex, "i");
    return function methodFilter(flow){
        return flow.request && regex.test(flow.request.method);
    };
}
function noResponseFilter(flow){
    return flow.request && !flow.response;
}
function responseFilter(flow){
    return !!flow.response;
}

function contentType(regex){
    regex = new RegExp(regex, "i");
    return function contentTypeFilter(flow){
        return (
            (flow.request && regex.test(RequestUtils.getContentType(flow.request)))
            ||
            (flow.response && regex.test(ResponseUtils.getContentType(flow.response)))
        );
    };
}
function requestContentType(regex){
    regex = new RegExp(regex, "i");
    return function requestContentTypeFilter(flow){
        return flow.request && regex.test(RequestUtils.getContentType(flow.request));
    };
}
function responseContentType(regex){
    regex = new RegExp(regex, "i");
    return function responseContentTypeFilter(flow){
        return flow.response && regex.test(ResponseUtils.getContentType(flow.response));
    };
}
function url(regex){
    regex = new RegExp(regex, "i");
    return function urlFilter(flow){
        return flow.request && regex.test(RequestUtils.pretty_url(flow.request));
    }
}
}

start "filter expression"
  = __ orExpr:OrExpr __ { return orExpr; }

ws "whitespace" = [ \t\n\r]
cc "control character" = [|&!()~"]
__ "optional whitespace" = ws*

OrExpr
  = first:AndExpr __ "|" __ second:OrExpr 
    { return or(first, second); }
  / AndExpr

AndExpr
  = first:NotExpr __ "&" __ second:AndExpr 
    { return and(first, second); }
  / first:NotExpr ws+ second:AndExpr 
    { return and(first, second); }
  / NotExpr

NotExpr
  = "!" __ expr:NotExpr 
    { return not(expr); }
  / BindingExpr

BindingExpr
  = "(" __ expr:OrExpr __ ")" 
    { return binding(orExpr); }
  / Expr

Expr
  = NullaryExpr
  / UnaryExpr

NullaryExpr
  = BooleanLiteral
  / "~a" { return assetFilter; }
  / "~e" { return errorFilter; }
  / "~q" { return noResponseFilter; }
  / "~s" { return responseFilter; }


BooleanLiteral
  = "true" { return trueFilter; }
  / "false" { return falseFilter; }

UnaryExpr
  = "~c"  ws+ s:StringLiteral { return responseCode(s); }
  / "~d"  ws+ s:StringLiteral { return domain(s); }
  / "~h"  ws+ s:StringLiteral { return header(s); }
  / "~hq" ws+ s:StringLiteral { return requestHeader(s); }
  / "~hs" ws+ s:StringLiteral { return responseHeader(s); }
  / "~m"  ws+ s:StringLiteral { return method(s); }
  / "~t"  ws+ s:StringLiteral { return contentType(s); }
  / "~tq" ws+ s:StringLiteral { return requestContentType(s); }
  / "~ts" ws+ s:StringLiteral { return responseContentType(s); }
  / "~u"  ws+ s:StringLiteral { return url(s); }
  / s:StringLiteral { return url(s); }

StringLiteral "string"
  = '"' chars:DoubleStringChar* '"' { return chars.join(""); }
  / "'" chars:SingleStringChar* "'" { return chars.join(""); }
  / !cc chars:UnquotedStringChar+ { return chars.join(""); }

DoubleStringChar
  = !["\\] char:. { return char; }
  / "\\" char:EscapeSequence { return char; }

SingleStringChar
  = !['\\] char:. { return char; }
  / "\\" char:EscapeSequence { return char; }

UnquotedStringChar
  = !ws char:. { return char; }

EscapeSequence
  = ['"\\]
  / "n" { return "\n"; }
  / "r" { return "\r"; }
  / "t" { return "\t"; }