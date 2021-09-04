import io
from typing import List, Optional, Tuple

from kaitaistruct import KaitaiStream

from mitmproxy.contrib.kaitaistruct import tls_client_hello
from mitmproxy.net import check


class ClientHello:

    def __init__(self, raw_client_hello):
        self._client_hello = tls_client_hello.TlsClientHello(
            KaitaiStream(io.BytesIO(raw_client_hello))
        )

    @property
    def cipher_suites(self) -> List[int]:
        return self._client_hello.cipher_suites.cipher_suites

    @property
    def sni(self) -> Optional[str]:
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                is_valid_sni_extension = (
                        extension.type == 0x00 and
                        len(extension.body.server_names) == 1 and
                        extension.body.server_names[0].name_type == 0 and
                        check.is_valid_host(extension.body.server_names[0].host_name)
                )
                if is_valid_sni_extension:
                    return extension.body.server_names[0].host_name.decode("ascii")
        return None

    @property
    def alpn_protocols(self) -> List[bytes]:
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                if extension.type == 0x10:
                    return list(x.name for x in extension.body.alpn_protocols)
        return []

    @property
    def extensions(self) -> List[Tuple[int, bytes]]:
        ret = []
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                body = getattr(extension, "_raw_body", extension.body)
                ret.append((extension.type, body))
        return ret

    def __repr__(self):
        return f"ClientHello(sni: {self.sni}, alpn_protocols: {self.alpn_protocols})"
