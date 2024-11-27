"""
This script is an example of how to manipulate cookies both outgoing (requests)
and ingoing (responses). In particular, this script inserts a cookie (specified
in a json file) into every request (overwriting any existing cookie of the same
name), and removes cookies from every response that have a certain set of names
specified in the variable (set) FILTER_COOKIES.

Usage:

    mitmproxy -s examples/contrib/http_manipulate_cookies.py

Note:
    this was created as a response to SO post:
    https://stackoverflow.com/questions/55358072/cookie-manipulation-in-mitmproxy-requests-and-responses

"""

import json

from mitmproxy import http

PATH_TO_COOKIES = "./cookies.json"  # insert your path to the cookie file here
FILTER_COOKIES = {
    "mycookie",
    "_ga",
}  # update this to the specific cookie names you want to remove
# NOTE: use a set for lookup efficiency


# -- Helper functions --
def load_json_cookies() -> list[dict[str, str | None]]:
    """
    Load a particular json file containing a list of cookies.
    """
    with open(PATH_TO_COOKIES) as f:
        return json.load(f)


# NOTE: or just hardcode the cookies as [{"name": "", "value": ""}]


def stringify_cookies(cookies: list[dict[str, str | None]]) -> str:
    """
    Creates a cookie string from a list of cookie dicts.
    """
    return "; ".join(
        [
            f"{c['name']}={c['value']}"
            if c.get("value", None) is not None
            else f"{c['name']}"
            for c in cookies
        ]
    )


def parse_cookies(cookie_string: str) -> list[dict[str, str | None]]:
    """
    Parses a cookie string into a list of cookie dicts.
    """
    return [
        {"name": g[0], "value": g[1]} if len(g) == 2 else {"name": g[0], "value": None}
        for g in [
            k.split("=", 1) for k in [c.strip() for c in cookie_string.split(";")] if k
        ]
    ]


# -- Main interception functionality --
def request(flow: http.HTTPFlow) -> None:
    """Add a specific set of cookies to every request."""
    # obtain any cookies from the request
    _req_cookies_str = flow.request.headers.get("cookie", "")
    req_cookies = parse_cookies(_req_cookies_str)

    # add our cookies to the original cookies from the request
    all_cookies = req_cookies + load_json_cookies()
    # NOTE: by adding it to the end we should overwrite any existing cookies
    # of the same name but if you want to be more careful you can iterate over
    # the req_cookies and remove the ones you want to overwrite first.

    # modify the request with the combined cookies
    flow.request.headers["cookie"] = stringify_cookies(all_cookies)


def response(flow: http.HTTPFlow) -> None:
    """Remove a specific cookie from every response."""
    set_cookies_str = flow.response.headers.get_all("set-cookie")
    # NOTE: According to docs, for use with the "Set-Cookie" and "Cookie" headers, either use `Response.cookies` or see `Headers.get_all`.
    set_cookies_str_modified: list[str] = []

    if set_cookies_str:
        for cookie in set_cookies_str:
            resp_cookies = parse_cookies(cookie)

            # remove the cookie we want to remove
            resp_cookies = [c for c in resp_cookies if c["name"] not in FILTER_COOKIES]

            # append the modified cookies to the list that will change the requested cookies
            set_cookies_str_modified.append(stringify_cookies(resp_cookies))

        # modify the request with the combined cookies
        flow.response.headers.set_all("set-cookie", set_cookies_str_modified)
