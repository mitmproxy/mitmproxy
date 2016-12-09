import logging

import cssutils

from . import base


class ViewCSS(base.View):
    name = "CSS"
    prompt = ("css", "c")
    content_types = [
        "text/css"
    ]

    def __call__(self, data, **metadata):
        cssutils.log.setLevel(logging.CRITICAL)
        cssutils.ser.prefs.keepComments = True
        cssutils.ser.prefs.omitLastSemicolon = False
        cssutils.ser.prefs.indentClosingBrace = False
        cssutils.ser.prefs.validOnly = False

        sheet = cssutils.parseString(data)
        beautified = sheet.cssText

        return "CSS", base.format_text(beautified)
