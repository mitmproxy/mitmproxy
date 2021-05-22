import _ from 'lodash'
import React from 'react'

window._ = _;
window.React = React;

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


export var formatTimeStamp = function (seconds, utc_to_local=true) {
    var utc = new Date(seconds * 1000);
    if (utc_to_local) {
        var local = utc.getTime() - utc.getTimezoneOffset() * 60 * 1000;
        var ts = new Date(local).toISOString();
    } else {
        var ts = utc.toISOString();
    }
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
const xsrf = `_xsrf=${getCookie("_xsrf")}`;

export function fetchApi(url, options={}) {
    if (options.method && options.method !== "GET") {
        if (url.indexOf("?") === -1) {
            url += "?" + xsrf;
        } else {
            url += "&" + xsrf;
        }
    } else {
        url += '.json'
    }
    if (url.startsWith("/")) {
        url = "." + url;
    }

    return fetch(url, {
        credentials: 'same-origin',
        ...options
    });
}

fetchApi.put = (url, json, options) => fetchApi(
    url,
    {
        method: "PUT",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(json),
        ...options
    }
)
// deep comparison of two json objects (dicts). arrays are handeled as a single value.
// return: json object including only the changed keys value pairs.
export function getDiff(obj1, obj2) {
    let result = {...obj2};
    for(let key in obj1) {
        if(_.isEqual(obj2[key], obj1[key]))
            result[key] = undefined
        else if(Object.prototype.toString.call(obj2[key]) === '[object Object]' &&
                Object.prototype.toString.call(obj1[key]) === '[object Object]' )
            result[key] = getDiff(obj1[key], obj2[key])
    }
    return result
}

export const pure = renderFn => class extends React.PureComponent {
    static displayName = renderFn.name

    render() {
        return renderFn(this.props)
    }
}
