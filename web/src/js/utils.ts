import { isEqual } from "lodash";
import * as React from "react";
import type { ContentViewData } from "./components/contentviews/useContentView";

window.React = React;

type JsonObject = Record<string, unknown>;
type CommandResult = {
    value?: any;
    error?: string;
};

export const formatSize = function (bytes: number | string): string {
    bytes = Number(bytes);
    if (bytes === 0) return "0";
    const prefix = ["b", "kb", "mb", "gb", "tb"];
    let i = 0;
    for (; i < prefix.length; i++) {
        if (Math.pow(1024, i + 1) > bytes) {
            break;
        }
    }
    let precision: number;
    if (bytes % Math.pow(1024, i) === 0) precision = 0;
    else precision = 1;
    return (bytes / Math.pow(1024, i)).toFixed(precision) + prefix[i];
};

export const formatTimeDelta = function (milliseconds: number): string {
    let time = milliseconds;
    const prefix = ["ms", "s", "min", "h"];
    const div = [1000, 60, 60];
    let i = 0;
    while (Math.abs(time) >= div[i] && i < div.length) {
        time = time / div[i];
        i++;
    }
    return Math.round(time) + prefix[i];
};

export const formatTimeStamp = function (
    seconds: number,
    { includeMilliseconds = true } = {},
): string {
    const date = new Date(seconds * 1000);

    const yearStr = String(date.getFullYear());
    const monthStr = String(date.getMonth() + 1).padStart(2, "0");
    const dayStr = String(date.getDate()).padStart(2, "0");
    const hourStr = String(date.getHours()).padStart(2, "0");
    const minuteStr = String(date.getMinutes()).padStart(2, "0");
    const secondStr = String(date.getSeconds()).padStart(2, "0");
    const millisecondStr = String(date.getMilliseconds()).padStart(3, "0");

    let timestamp = `${yearStr}-${monthStr}-${dayStr} ${hourStr}:${minuteStr}:${secondStr}`;
    if (includeMilliseconds) timestamp += `.${millisecondStr}`;

    return timestamp;
};

export function formatAddress(address: [string, number]): string {
    if (address[0].includes(":")) {
        return `[${address[0]}]:${address[1]}`;
    } else {
        return `${address[0]}:${address[1]}`;
    }
}

// At some places, we need to sort strings alphabetically descending,
// but we can only provide a key function.
// This beauty "reverses" a JS string.
const end = String.fromCharCode(0xffff);

export function reverseString(s: string): string {
    return (
        String.fromCharCode(
            ...s.split("").map((c) => 0xffff - c.charCodeAt(0)),
        ) + end
    );
}

function getCookie(name: string): string | undefined {
    const r = document.cookie.match(new RegExp("\\b" + name + "=([^;]*)\\b"));
    return r ? r[1] : undefined;
}

let xsrf: () => string | undefined = () => {
    const cached = getCookie("_mitmproxy_xsrf");
    xsrf = () => cached;
    return xsrf();
};

export function fetchApi (
    url: string,
    options: RequestInit = {},
): Promise<Response> {
    if (options.method && options.method !== "GET") {
        const headers = new Headers(options.headers);
        const token = xsrf();
        if (token) {
            headers.set("X-XSRFToken", token);
        }
        options.headers = headers;
    }
    if (url.startsWith("/")) {
        url = "." + url;
    }

    return fetch(url, {
        credentials: "same-origin",
        ...options,
    });
};

fetchApi.put = (url: string, json: unknown, options: RequestInit = {}) =>
    fetchApi(url, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(json),
        ...options,
    });

fetchApi.post = (url: string, json: unknown, options: RequestInit = {}) =>
    fetchApi(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(json),
        ...options,
    });

export async function runCommand(
    command: string,
    ...args: string[]
): Promise<CommandResult> {
    const response = await fetchApi(`/commands/${command}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ arguments: args }),
    });
    return await response.json();
}

function isPlainObject(value: unknown): value is JsonObject {
    return Object.prototype.toString.call(value) === "[object Object]";
}

// deep comparison of two json objects (dicts). arrays are handeled as a single value.
// return: json object including only the changed keys value pairs.
export function getDiff(obj1: JsonObject, obj2: JsonObject): JsonObject {
    const result = { ...obj2 };
    for (const key in obj1) {
        if (isEqual(obj2[key], obj1[key])) result[key] = undefined;
        else if (isPlainObject(obj2[key]) && isPlainObject(obj1[key]))
            result[key] = getDiff(obj1[key], obj2[key]);
    }
    return result;
}

/**
 * `navigator.clipboard.writeText()`, but with an additional fallback for non-secure contexts.
 *
 * Never throws unless textPromise is rejected.
 */
export async function copyToClipboard(
    textPromise: Promise<string>,
): Promise<void> {
    // Try the new clipboard APIs first. If that fails, use textarea fallback.
    try {
        await navigator.clipboard.write([
            new ClipboardItem({
                "text/plain": textPromise,
            }),
        ]);
        return;
    } catch (err) {
        console.warn(err);
    }

    const text = await textPromise;

    try {
        await navigator.clipboard.writeText(text);
        return;
    } catch (err) {
        console.warn(err);
    }

    const t = document.createElement("textarea");
    t.value = text;
    t.style.position = "absolute";
    t.style.opacity = "0";
    document.body.appendChild(t);
    try {
        t.focus();
        t.select();
        if (!document.execCommand("copy")) {
            throw new Error("failed to copy");
        }
    } catch {
        alert(text);
    } finally {
        t.remove();
    }
}

export async function copyViewContentDataToClipboard(
    contentViewData: ContentViewData | undefined,
): Promise<void> {
    await copyToClipboard(Promise.resolve(contentViewData?.text || ""));
}

export function rpartition(str: string, sep: string): [string, string] {
    const lastIndex = str.lastIndexOf(sep);
    if (lastIndex === -1) {
        return ["", str];
    }
    const before = str.slice(0, lastIndex);
    const after = str.slice(lastIndex + sep.length);
    return [before, after];
}

/** A JS equivalent of Python's https://docs.python.org/3/library/stdtypes.html#str.partition */
export function partition(str: string, sep: string): [string, string] {
    const index = str.indexOf(sep);
    if (index === -1) {
        return [str, ""];
    }
    const before = str.slice(0, index);
    const after = str.slice(index + sep.length);
    return [before, after];
}

/* istanbul ignore next @preserve */
export function assertNever(val: never): never {
    throw new Error(`Unreachable: ${JSON.stringify(val)}`);
}
