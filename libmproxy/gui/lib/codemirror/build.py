files = ["codemirror.js",
         "mode-javascript.js",
         "addon/edit/continuecomment.js",
         "addon/format/formatting.js",
         "addon/hint/simple-hint.js",
         "addon/hint/javascript-hint.js",
         "addon/edit/matchbrackets.js",
         "addon/search/searchcursor.js",
         "addon/search/match-highlighter.js"]
with open("codemirror.combined.js", "w") as out:
    out.write("// Combined build\n")
    out.write("// Files: %s\n\n" % " ".join(files))
    for srcfile in files:
        with open(srcfile,"r") as src:
            out.write(src.read())
