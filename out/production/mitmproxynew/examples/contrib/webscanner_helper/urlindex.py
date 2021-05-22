import abc
import datetime
import json
import logging
from pathlib import Path
from typing import Type, Dict, Union, Optional

from mitmproxy import flowfilter
from mitmproxy.http import HTTPFlow

logger = logging.getLogger(__name__)


class UrlIndexWriter(abc.ABC):
    """Abstract Add-on to write seen URLs.

    For example, these URLs can be injected in a web application to improve the crawling of web application scanners.
    The injection can be done using the URLInjection Add-on.
    """

    def __init__(self, filename: Path):
        """Initializes the UrlIndexWriter.

        Args:
            filename: Path to file to which the URL index will be written.
        """
        self.filepath = filename

    @abc.abstractmethod
    def load(self):
        """Load existing URL index."""
        pass

    @abc.abstractmethod
    def add_url(self, flow: HTTPFlow):
        """Add new URL to URL index."""
        pass

    @abc.abstractmethod
    def save(self):
        pass


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class JSONUrlIndexWriter(UrlIndexWriter):
    """Writes seen URLs as JSON."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_urls = {}

    def load(self):
        if self.filepath.exists():
            with self.filepath.open("r") as f:
                self.host_urls = json.load(f)
            for host in self.host_urls.keys():
                for path, methods in self.host_urls[host].items():
                    for method, codes in methods.items():
                        self.host_urls[host][path] = {method: set(codes)}

    def add_url(self, flow: HTTPFlow):
        req = flow.request
        res = flow.response

        if req is not None and res is not None:
            urls = self.host_urls.setdefault(f"{req.scheme}://{req.host}:{req.port}", dict())
            methods = urls.setdefault(req.path, {})
            codes = methods.setdefault(req.method, set())
            codes.add(res.status_code)

    def save(self):
        with self.filepath.open("w") as f:
            json.dump(self.host_urls, f, cls=SetEncoder)


class TextUrlIndexWriter(UrlIndexWriter):
    """Writes seen URLs as text."""

    def load(self):
        pass

    def add_url(self, flow: HTTPFlow):
        res = flow.response
        req = flow.request
        if res is not None and req is not None:
            with self.filepath.open("a+") as f:
                f.write(f"{datetime.datetime.utcnow().isoformat()} STATUS: {res.status_code} METHOD: "
                        f"{req.method} URL:{req.url}\n")

    def save(self):
        pass


WRITER: Dict[str, Type[UrlIndexWriter]] = {
    "json": JSONUrlIndexWriter,
    "text": TextUrlIndexWriter,
}


def filter_404(flow) -> bool:
    """Filters responses with status code 404."""
    return flow.response.status_code != 404


class UrlIndexAddon:
    """Add-on to write seen URLs, either as JSON or as text.

    For example, these URLs can be injected in a web application to improve the crawling of web application scanners.
    The injection can be done using the URLInjection Add-on.
    """

    index_filter: Optional[Union[str, flowfilter.TFilter]]
    writer: UrlIndexWriter

    OPT_FILEPATH = "URLINDEX_FILEPATH"
    OPT_APPEND = "URLINDEX_APPEND"
    OPT_INDEX_FILTER = "URLINDEX_FILTER"

    def __init__(self, file_path: Union[str, Path], append: bool = True,
                 index_filter: Union[str, flowfilter.TFilter] = filter_404, index_format: str = "json"):
        """ Initializes the urlindex add-on.

        Args:
            file_path: Path to file to which the URL index will be written. Can either be given as str or Path.
            append: Bool to decide whether to append new URLs to the given file (as opposed to overwrite the contents
                of the file)
            index_filer: A mitmproxy filter with which the seen URLs will be filtered before being written. Can either
                be given as str or as flowfilter.TFilter
            index_format: The format of the URL index, can either be "json" or "text".
        """

        if isinstance(index_filter, str):
            self.index_filter = flowfilter.parse(index_filter)
            if self.index_filter is None:
                raise ValueError("Invalid filter expression.")
        else:
            self.index_filter = index_filter

        file_path = Path(file_path)
        try:
            self.writer = WRITER[index_format.lower()](file_path)
        except KeyError:
            raise ValueError(f"Format '{index_format}' is not supported.")

        if not append and file_path.exists():
            file_path.unlink()

        self.writer.load()

    def response(self, flow: HTTPFlow):
        """Checks if the response should be included in the URL based on the index_filter and adds it to the URL index
            if appropriate.
        """
        if isinstance(self.index_filter, str) or self.index_filter is None:
            raise ValueError("Invalid filter expression.")
        else:
            if self.index_filter(flow):
                self.writer.add_url(flow)

    def done(self):
        """Writes the URL index."""
        self.writer.save()
