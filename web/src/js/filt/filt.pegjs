// PEG.js filter rules - see http://pegjs.majda.cz/online

/* Explain Filter */
{
  var or = function(first, second) {
    return first + " or " + second;
  };
  var and = function(first, second) {
    return first + " and " + second;
  };
  var not = function(expr) {
    return "not " + expr;
  };
  var binding = function(expr) {
    return "(" + expr + ")";
  }
  var assetFilter = "is asset";
  var trueFilter = true;
  var falseFilter = false;
  var bodyFilter = function(s) {
    return "body ~= '" + s + "'";
  }
  var urlFilter = function(s) {
    return "url ~= '" + s + "'";
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
  / "~a" { return assetFilter; };

BooleanLiteral
  = "true" { return trueFilter; }
  / "false" { return falseFilter; }

UnaryExpr
  = "~b" ws+ s:StringLiteral { return bodyFilter(s); }
  / s:StringLiteral { return urlFilter(s); }

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