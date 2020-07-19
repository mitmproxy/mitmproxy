import time
import urllib.parse
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple, Union

import mitmproxy.net.http.url
from mitmproxy.coretypes import multidict
from mitmproxy.net.http import cookies, multipart
from mitmproxy.net.http import message
from mitmproxy.net.http.headers import Headers
from mitmproxy.utils.strutils import always_bytes, always_str


@dataclass
class RequestData(message.MessageData):
    host: str
    port: int
    method: bytes
    scheme: bytes
    authority: bytes
    path: bytes


class Request(message.Message):
    """
    An HTTP request.
    """
    data: RequestData

    def __init__(
            self,
            host: str,
            port: int,
            method: bytes,
            scheme: bytes,
            authority: bytes,
            path: bytes,
            http_version: bytes,
            headers: Union[Headers, Tuple[Tuple[bytes, bytes], ...]],
            content: Optional[bytes],
            trailers: Union[None, Headers, Tuple[Tuple[bytes, bytes], ...]],
            timestamp_start: float,
            timestamp_end: Optional[float],
    ):
        # auto-convert invalid types to retain compatibility with older code.
        if isinstance(host, bytes):
            host = host.decode("idna", "strict")
        if isinstance(method, str):
            method = method.encode("ascii", "strict")
        if isinstance(scheme, str):
            scheme = scheme.encode("ascii", "strict")
        if isinstance(authority, str):
            authority = authority.encode("ascii", "strict")
        if isinstance(path, str):
            path = path.encode("ascii", "strict")
        if isinstance(http_version, str):
            http_version = http_version.encode("ascii", "strict")

        if isinstance(content, str):
            raise ValueError(f"Content must be bytes, not {type(content).__name__}")
        if not isinstance(headers, Headers):
            headers = Headers(headers)
        if trailers is not None and not isinstance(trailers, Headers):
            trailers = Headers(trailers)

        self.data = RequestData(
            host=host,
            port=port,
            method=method,
            scheme=scheme,
            authority=authority,
            path=path,
            http_version=http_version,
            headers=headers,
            content=content,
            trailers=trailers,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

    def __repr__(self) -> str:
        if self.host and self.port:
            hostport = f"{self.host}:{self.port}"
        else:
            hostport = ""
        path = self.path or ""
        return f"Request({self.method} {hostport}{path})"

    @classmethod
    def make(
            cls,
            method: str,
            url: str,
            content: Union[bytes, str] = "",
            headers: Union[Headers, Dict[Union[str, bytes], Union[str, bytes]], Iterable[Tuple[bytes, bytes]]] = ()
    ) -> "Request":
        """
        Simplified API for creating request objects.
        """
        # Headers can be list or dict, we differentiate here.
        if isinstance(headers, Headers):
            pass
        elif isinstance(headers, dict):
            headers = Headers(
                (always_bytes(k, "utf-8", "surrogateescape"),
                 always_bytes(v, "utf-8", "surrogateescape"))
                for k, v in headers.items()
            )
        elif isinstance(headers, Iterable):
            headers = Headers(headers)
        else:
            raise TypeError("Expected headers to be an iterable or dict, but is {}.".format(
                type(headers).__name__
            ))

        req = cls(
            "",
            0,
            method.encode("utf-8", "surrogateescape"),
            b"",
            b"",
            b"",
            b"HTTP/1.1",
            headers,
            b"",
            None,
            time.time(),
            time.time(),
        )

        req.url = url
        # Assign this manually to update the content-length header.
        if isinstance(content, bytes):
            req.content = content
        elif isinstance(content, str):
            req.text = content
        else:
            raise TypeError(f"Expected content to be str or bytes, but is {type(content).__name__}.")

        return req

    @property
    def first_line_format(self) -> str:
        """
        HTTP request form as defined in `RFC7230 <https://tools.ietf.org/html/rfc7230#section-5.3>`_.

        origin-form and asterisk-form are subsumed as "relative".
        """
        if self.method == "CONNECT":
            return "authority"
        elif self.authority:
            return "absolute"
        else:
            return "relative"

    @property
    def method(self) -> str:
        """
        HTTP request method, e.g. "GET".
        """
        return self.data.method.decode("utf-8", "surrogateescape").upper()

    @method.setter
    def method(self, val: Union[str, bytes]) -> None:
        self.data.method = always_bytes(val, "utf-8", "surrogateescape")

    @property
    def scheme(self) -> str:
        """
        HTTP request scheme, which should be "http" or "https".
        """
        return self.data.scheme.decode("utf-8", "surrogateescape")

    @scheme.setter
    def scheme(self, val: Union[str, bytes]) -> None:
        self.data.scheme = always_bytes(val, "utf-8", "surrogateescape")

    @property
    def authority(self) -> str:
        """
        HTTP request authority.

        For HTTP/1, this is the authority portion of the request target
        (in either absolute-form or authority-form)

        For HTTP/2, this is the :authority pseudo header.
        """
        try:
            return self.data.authority.decode("idna")
        except UnicodeError:
            return self.data.authority.decode("utf8", "surrogateescape")

    @authority.setter
    def authority(self, val: Union[str, bytes]) -> None:
        if isinstance(val, str):
            try:
                val = val.encode("idna", "strict")
            except UnicodeError:
                val = val.encode("utf8", "surrogateescape")  # type: ignore
        self.data.authority = val

    @property
    def host(self) -> str:
        """
        Target host. This may be parsed from the raw request
        (e.g. from a ``GET http://example.com/ HTTP/1.1`` request line)
        or inferred from the proxy mode (e.g. an IP in transparent mode).

        Setting the host attribute also updates the host header and authority information, if present.
        """
        return self.data.host

    @host.setter
    def host(self, val: Union[str, bytes]) -> None:
        self.data.host = always_str(val, "idna", "strict")

        # Update host header
        if "Host" in self.data.headers:
            self.data.headers["Host"] = val
        # Update authority
        if self.data.authority:
            self.authority = mitmproxy.net.http.url.hostport(self.scheme, self.host, self.port)

    @property
    def host_header(self) -> Optional[str]:
        """
        The request's host/authority header.

        This property maps to either ``request.headers["Host"]`` or
        ``request.authority``, depending on whether it's HTTP/1.x or HTTP/2.0.
        """
        if self.is_http2:
            return self.authority or self.data.headers.get("Host", None)
        else:
            return self.data.headers.get("Host", None)

    @host_header.setter
    def host_header(self, val: Union[None, str, bytes]) -> None:
        if val is None:
            if self.is_http2:
                self.data.authority = b""
            self.headers.pop("Host", None)
        else:
            if self.is_http2:
                self.authority = val  # type: ignore
            if not self.is_http2 or "Host" in self.headers:
                # For h2, we only overwrite, but not create, as :authority is the h2 host header.
                self.headers["Host"] = val

    @property
    def port(self) -> int:
        """
        Target port
        """
        return self.data.port

    @port.setter
    def port(self, port: int) -> None:
        self.data.port = port

    @property
    def path(self) -> str:
        """
        HTTP request path, e.g. "/index.html".
        Usually starts with a slash, except for OPTIONS requests, which may just be "*".
        """
        return self.data.path.decode("utf-8", "surrogateescape")

    @path.setter
    def path(self, val: Union[str, bytes]) -> None:
        self.data.path = always_bytes(val, "utf-8", "surrogateescape")

    @property
    def url(self) -> str:
        """
        The URL string, constructed from the request's URL components.
        """
        if self.first_line_format == "authority":
            return f"{self.host}:{self.port}"
        return mitmproxy.net.http.url.unparse(self.scheme, self.host, self.port, self.path)

    @url.setter
    def url(self, val: Union[str, bytes]) -> None:
        val = always_str(val, "utf-8", "surrogateescape")
        self.scheme, self.host, self.port, self.path = mitmproxy.net.http.url.parse(val)

    @property
    def pretty_host(self) -> str:
        """
        Similar to :py:attr:`host`, but using the host/:authority header as an additional (preferred) data source.
        This is useful in transparent mode where :py:attr:`host` is only an IP address,
        but may not reflect the actual destination as the Host header could be spoofed.
        """
        authority = self.host_header
        if authority:
            return mitmproxy.net.http.url.parse_authority(authority, check=False)[0]
        else:
            return self.host

    @property
    def pretty_url(self) -> str:
        """
        Like :py:attr:`url`, but using :py:attr:`pretty_host` instead of :py:attr:`host`.
        """
        if self.first_line_format == "authority":
            return self.authority

        host_header = self.host_header
        if not host_header:
            return self.url

        pretty_host, pretty_port = mitmproxy.net.http.url.parse_authority(host_header, check=False)
        pretty_port = pretty_port or mitmproxy.net.http.url.default_port(self.scheme) or 443

        return mitmproxy.net.http.url.unparse(self.scheme, pretty_host, pretty_port, self.path)

    def _get_query(self):
        query = urllib.parse.urlparse(self.url).query
        return tuple(mitmproxy.net.http.url.decode(query))

    def _set_query(self, query_data):
        query = mitmproxy.net.http.url.encode(query_data)
        _, _, path, params, _, fragment = urllib.parse.urlparse(self.url)
        self.path = urllib.parse.urlunparse(["", "", path, params, query, fragment])

    @property
    def query(self) -> multidict.MultiDictView:
        """
        The request query string as an :py:class:`~mitmproxy.net.multidict.MultiDictView` object.
        """
        return multidict.MultiDictView(
            self._get_query,
            self._set_query
        )

    @query.setter
    def query(self, value):
        self._set_query(value)

    def _get_cookies(self):
        h = self.headers.get_all("Cookie")
        return tuple(cookies.parse_cookie_headers(h))

    def _set_cookies(self, value):
        self.headers["cookie"] = cookies.format_cookie_header(value)

    @property
    def cookies(self) -> multidict.MultiDictView:
        """
        The request cookies.

        An empty :py:class:`~mitmproxy.net.multidict.MultiDictView` object if the cookie monster ate them all.
        """
        return multidict.MultiDictView(
            self._get_cookies,
            self._set_cookies
        )

    @cookies.setter
    def cookies(self, value):
        self._set_cookies(value)

    @property
    def path_components(self):
        """
        The URL's path components as a tuple of strings.
        Components are unquoted.
        """
        path = urllib.parse.urlparse(self.url).path
        # This needs to be a tuple so that it's immutable.
        # Otherwise, this would fail silently:
        #   request.path_components.append("foo")
        return tuple(mitmproxy.net.http.url.unquote(i) for i in path.split("/") if i)

    @path_components.setter
    def path_components(self, components):
        components = map(lambda x: mitmproxy.net.http.url.quote(x, safe=""), components)
        path = "/" + "/".join(components)
        _, _, _, params, query, fragment = urllib.parse.urlparse(self.url)
        self.path = urllib.parse.urlunparse(["", "", path, params, query, fragment])

    def anticache(self) -> None:
        """
        Modifies this request to remove headers that might produce a cached
        response. That is, we remove ETags and If-Modified-Since headers.
        """
        delheaders = [
            "if-modified-since",
            "if-none-match",
        ]
        for i in delheaders:
            self.headers.pop(i, None)

    def anticomp(self) -> None:
        """
        Modifies this request to remove headers that will compress the
        resource's data.
        """
        self.headers["accept-encoding"] = "identity"

    def constrain_encoding(self) -> None:
        """
        Limits the permissible Accept-Encoding values, based on what we can
        decode appropriately.
        """
        accept_encoding = self.headers.get("accept-encoding")
        if accept_encoding:
            self.headers["accept-encoding"] = (
                ', '.join(
                    e
                    for e in {"gzip", "identity", "deflate", "br", "zstd"}
                    if e in accept_encoding
                )
            )

    def _get_urlencoded_form(self):
        is_valid_content_type = "application/x-www-form-urlencoded" in self.headers.get("content-type", "").lower()
        if is_valid_content_type:
            return tuple(mitmproxy.net.http.url.decode(self.get_text(strict=False)))
        return ()

    def _set_urlencoded_form(self, form_data):
        """
        Sets the body to the URL-encoded form data, and adds the appropriate content-type header.
        This will overwrite the existing content if there is one.
        """
        self.headers["content-type"] = "application/x-www-form-urlencoded"
        self.content = mitmproxy.net.http.url.encode(form_data, self.get_text(strict=False)).encode()

    @property
    def urlencoded_form(self):
        """
        The URL-encoded form data as an :py:class:`~mitmproxy.net.multidict.MultiDictView` object.
        An empty multidict.MultiDictView if the content-type indicates non-form data
        or the content could not be parsed.

        Starting with mitmproxy 1.0, key and value are strings.
        """
        return multidict.MultiDictView(
            self._get_urlencoded_form,
            self._set_urlencoded_form
        )

    @urlencoded_form.setter
    def urlencoded_form(self, value):
        self._set_urlencoded_form(value)

    def _get_multipart_form(self):
        is_valid_content_type = "multipart/form-data" in self.headers.get("content-type", "").lower()
        if is_valid_content_type:
            try:
                return multipart.decode(self.headers, self.content)
            except ValueError:
                pass
        return ()

    def _set_multipart_form(self, value):
        self.content = mitmproxy.net.http.multipart.encode(self.headers, value)
        self.headers["content-type"] = "multipart/form-data"

    @property
    def multipart_form(self):
        """
        The multipart form data as an :py:class:`~mitmproxy.net.multidict.MultiDictView` object.
        An empty multidict.MultiDictView if the content-type indicates non-form data
        or the content could not be parsed.

        Key and value are bytes.
        """
        return multidict.MultiDictView(
            self._get_multipart_form,
            self._set_multipart_form
        )

    @multipart_form.setter
    def multipart_form(self, value):
        self._set_multipart_form(value)
