(function() {
  CodeMirror.defineOption("collapseRange", false, function(cm, val, old) {
    var wasOn = old && old != CodeMirror.Init;
    if (val && !wasOn)
      enableRangeCollapsing(cm);
    else if (!val && wasOn)
      disableRangeCollapsing(cm);
  });

  var gutterClass = "CodeMirror-collapserange";

  function enableRangeCollapsing(cm) {
    cm.on("gutterClick", gutterClick);
    cm.setOption("gutters", (cm.getOption("gutters") || []).concat([gutterClass]));
  }

  function disableRangeCollapsing(cm) {
    cm.rangeCollapseStart = null;
    cm.off("gutterClick", gutterClick);
    var gutters = cm.getOption("gutters");
    for (var i = 0; i < gutters.length && gutters[i] != gutterClass; ++i) {}
    cm.setOption("gutters", gutters.slice(0, i).concat(gutters.slice(i + 1)));
  }

  function gutterClick(cm, line, gutter) {
    if (gutter != gutterClass) return;

    var start = cm.rangeCollapseStart;
    if (start) {
      var old = cm.getLineNumber(start);
      cm.setGutterMarker(start, gutterClass, null);
      cm.rangeCollapseStart = null;
      var from = Math.min(old, line), to = Math.max(old, line);
      if (from != to) {
        // Finish this fold
        var fold = cm.markText({line: from + 1, ch: 0}, {line: to - 1}, {
          collapsed: true,
          inclusiveLeft: true,
          inclusiveRight: true,
          clearOnEnter: true
        });
        var clear = function() {
          cm.setGutterMarker(topLine, gutterClass, null);
          cm.setGutterMarker(botLine, gutterClass, null);
          fold.clear();
        };
        var topLine = cm.setGutterMarker(from, gutterClass, makeMarker(true, true, clear));
        var botLine = cm.setGutterMarker(to, gutterClass, makeMarker(false, true, clear));
        CodeMirror.on(fold, "clear", clear);

        return;
      }
    }

    // Start a new fold
    cm.rangeCollapseStart = cm.setGutterMarker(line, gutterClass, makeMarker(true, false));
  }

  function makeMarker(isTop, isFinished, handler) {
    var node = document.createElement("div");
    node.innerHTML = isTop ? "\u25bc" : "\u25b2";
    if (!isFinished) node.style.color = "red";
    node.style.fontSize = "85%";
    node.style.cursor = "pointer";
    if (handler) CodeMirror.on(node, "mousedown", handler);
    return node;
  }
})();
