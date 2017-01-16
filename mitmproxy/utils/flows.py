"""
This utility module provides additional utility methods that are directly
related to an HTTPFlow object.
"""
import hashlib
import typing
import urllib.parse

import mitmproxy.http


def hash_flow(flow: mitmproxy.http.HTTPFlow,
              include_headers_list: typing.Optional[list]=None,
              ignore_host: bool=False,
              ignore_content: bool=False,
              ignore_payload_params_list: typing.Optional[list]=None,
              ignore_query_params_list: typing.Optional[list]=None) -> str:
    """
    Calculates a loose hash of the flow request.

    The hash is based on the the port, scheme, method, host, path, parameters, and headers.
    Note that it is possible to filter certain parameters to be included in the hash with the
    `ignore_payload_params_list` and `ignore_query_params_list`.  The `include_headers_list` is a
    whitelist of headers.

    Args:
        flow: The flow object to generate a hash from
        include_headers_list: List of headers we want to include in the hash.
        ignore_host: Ignore the host when calculating the hash.
        ignore_content: Ignore the entirety of the payload content.
            Note: When this parameter is set to true, the `ignore_payload_params` and
            `ignore_query_params_list` parameters are ignored since they are mutually exclusive.
        ignore_payload_params_list: List of payload params that we want to ignore.
        ignore_query_params_list: List of query params that we want to ignore.

    Returns:
        Returns a hash string of the flow.
    """
    r = flow.request
    url_parsed = urllib.parse.urlparse(r.url)
    queries_array = urllib.parse.parse_qsl(url_parsed.query, keep_blank_values=True)

    key = [
        str(i)
        for i in {r.port, r.scheme, r.method, url_parsed.path}
    ]  # type: typing.List[typing.Any]
    if not ignore_host:
        key.append(r.host)

    # Is there payload any params we want to ignore?
    if not ignore_content:
        if ignore_payload_params_list and r.multipart_form:
            key.extend(
                (k, v)
                for k, v in r.multipart_form.items(multi=True)
                if k.decode(errors="replace") not in ignore_payload_params_list
            )
        elif ignore_payload_params_list and r.urlencoded_form:
            key.extend(
                (k, v)
                for k, v in r.urlencoded_form.items(multi=True)
                if k not in ignore_payload_params_list
            )
        # We don't care about the specifics of which content to include, include everything
        else:
            key.append(str(r.raw_content))

    # Is there any query params we want to ignore?
    for k, v in queries_array:
        if k not in ignore_query_params_list:
            key.append((k, v))

    # By default, we ignore headers, these params specify which headers to include
    if include_headers_list:
        headers = []
        for header_name in include_headers_list:
            header_value = r.headers.get(header_name)
            headers.append((header_name, header_value))
        key.append(headers)

    # Note: this was exactly how the key list was hashed before, not entirely sure as to why
    # exactly it was done this way, that is, the repr typecasting and encoding.
    return hashlib.sha256(repr(key).encode("utf8", "surrogateescape")).digest()
