import $ from "jquery";
import _ from "lodash";
import actions from "./actions.js";

window.$ = $;
window._ = _;
window.React = require("react");

export var Key = {
    UP: 38,
    DOWN: 40,
    PAGE_UP: 33,
    PAGE_DOWN: 34,
    HOME: 36,
    END: 35,
    LEFT: 37,
    RIGHT: 39,
    ENTER: 13,
    ESC: 27,
    TAB: 9,
    SPACE: 32,
    BACKSPACE: 8,
    SHIFT: 16
};
// Add A-Z
for (var i = 65; i <= 90; i++) {
    Key[String.fromCharCode(i)] = i;
}


export var formatSize = function (bytes) {
    if (bytes === 0)
        return "0";
    var prefix = ["b", "kb", "mb", "gb", "tb"];
    for (var i = 0; i < prefix.length; i++) {
        if (Math.pow(1024, i + 1) > bytes) {
            break;
        }
    }
    var precision;
    if (bytes % Math.pow(1024, i) === 0)
        precision = 0;
    else
        precision = 1;
    return (bytes / Math.pow(1024, i)).toFixed(precision) + prefix[i];
};


export var formatTimeDelta = function (milliseconds) {
    var time = milliseconds;
    var prefix = ["ms", "s", "min", "h"];
    var div = [1000, 60, 60];
    var i = 0;
    while (Math.abs(time) >= div[i] && i < div.length) {
        time = time / div[i];
        i++;
    }
    return Math.round(time) + prefix[i];
};


export var formatTimeStamp = function (seconds) {
    var ts = (new Date(seconds * 1000)).toISOString();
    return ts.replace("T", " ").replace("Z", "");
};

// At some places, we need to sort strings alphabetically descending,
// but we can only provide a key function.
// This beauty "reverses" a JS string.
var end = String.fromCharCode(0xffff);
export function reverseString(s) {
    return String.fromCharCode.apply(String,
            _.map(s.split(""), function (c) {
                return 0xffff - c.charCodeAt(0);
            })
        ) + end;
}

function getCookie(name) {
    var r = document.cookie.match(new RegExp("\\b" + name + "=([^;]*)\\b"));
    return r ? r[1] : undefined;
}
var xsrf = $.param({_xsrf: getCookie("_xsrf")});

//Tornado XSRF Protection.
$.ajaxPrefilter(function (options) {
    if (["post", "put", "delete"].indexOf(options.type.toLowerCase()) >= 0 && options.url[0] === "/") {
        if(options.url.indexOf("?") === -1){
            options.url += "?" + xsrf;
        } else {
            options.url += "&" + xsrf;
        }
    }
});
// Log AJAX Errors
$(document).ajaxError(function (event, jqXHR, ajaxSettings, thrownError) {
    if (thrownError === "abort") {
        return;
    }
    var message = jqXHR.responseText;
    console.error(thrownError, message, arguments);
    actions.EventLogActions.add_event(thrownError + ": " + message);
    alert(message);
});