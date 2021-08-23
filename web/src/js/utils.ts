import _ from 'lodash'
import * as React from 'react'

// @ts-ignore
window._ = _;
window.React = React;

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


export var formatTimeStamp = function (
    seconds: number,
    {milliseconds = true} = {}
) {
    let utc = new Date(seconds * 1000);
    let ts = utc.toISOString().replace("T", " ").replace("Z", "");
    if (!milliseconds)
        ts = ts.slice(0, -4);
    return ts;
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
    let r = document.cookie.match(new RegExp("\\b" + name + "=([^;]*)\\b"));
    return r ? r[1] : undefined;
}

const xsrf = getCookie("_xsrf");

export function fetchApi(url: string, options: RequestInit = {}): Promise<Response> {
    if (options.method && options.method !== "GET") {
        options.headers = options.headers || {};
        options.headers["X-XSRFToken"] = xsrf;
    }
    if (url.startsWith("/")) {
        url = "." + url;
    }

    return fetch(url, {
        credentials: 'same-origin',
        ...options
    });
}

fetchApi.put = (url: string, json: any, options: RequestInit = {}) => fetchApi(
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


fetchApi.post = (url: string, json: any, options: RequestInit = {}) => fetchApi(
    url,
    {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(json),
        ...options
    }
)

export async function runCommand(command: string, ...args): Promise<any> {
    let response = await fetchApi(`/commands/${command}`, {
        method: 'POST', headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"arguments": args})
    });
    return await response.json()
}

// deep comparison of two json objects (dicts). arrays are handeled as a single value.
// return: json object including only the changed keys value pairs.
export function getDiff(obj1, obj2) {
    let result = {...obj2};
    for (let key in obj1) {
        if (_.isEqual(obj2[key], obj1[key]))
            result[key] = undefined
        else if (Object.prototype.toString.call(obj2[key]) === '[object Object]' &&
            Object.prototype.toString.call(obj1[key]) === '[object Object]')
            result[key] = getDiff(obj1[key], obj2[key])
    }
    return result
}
