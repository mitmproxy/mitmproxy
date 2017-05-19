export default function(){
    return {
    "client_conn": {
        "address": [
            "address",
            22
        ],
        "alpn_proto_negotiated": "http/1.1",
        "cipher_name": "cipher",
        "clientcert": null,
        "id": "75bfd3cd-a084-4d84-a063-b0804dc91342",
        "sni": "address",
        "ssl_established": false,
        "timestamp_end": 3.0,
        "timestamp_ssl_setup": 2.0,
        "timestamp_start": 1.0,
        "tls_version": "TLSv1.2"
    },
    "error": {
        "msg": "error",
        "timestamp": 1495158272.596447
    },
    "id": "8035b342-c916-44f7-93fa-293b40a7d3ad",
    "intercepted": false,
    "marked": false,
    "modified": false,
    "request": {
        "contentHash": "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73",
        "contentLength": 7,
        "headers": [
            [
                "header",
                "qvalue"
            ],
            [
                "content-length",
                "7"
            ]
        ],
        "host": "address",
        "http_version": "HTTP/1.1",
        "is_replay": false,
        "method": "GET",
        "path": "/path",
        "port": 22,
        "pretty_host": "address",
        "scheme": "http",
        "timestamp_end": null,
        "timestamp_start": null
    },
    "response": {
        "contentHash": "ab530a13e45914982b79f9b7e3fba994cfd1f3fb22f71cea1afbf02b460c6d1d",
        "contentLength": 7,
        "headers": [
            [
                "header-response",
                "svalue"
            ],
            [
                "content-length",
                "7"
            ]
        ],
        "http_version": "HTTP/1.1",
        "is_replay": false,
        "reason": "OK",
        "status_code": 200,
        "timestamp_end": 1495158272.5964308,
        "timestamp_start": 1495158272.5964305
    },
    "server_conn": {
        "address": [
            "address",
            22
        ],
        "alpn_proto_negotiated": null,
        "id": "9a5d01d7-ede8-4409-b064-230305bfa29d",
        "ip_address": [
            "192.168.0.1",
            22
        ],
        "sni": "address",
        "source_address": [
            "address",
            22
        ],
        "ssl_established": false,
        "timestamp_end": 4.0,
        "timestamp_ssl_setup": 3.0,
        "timestamp_start": 1.0,
        "timestamp_tcp_setup": 2.0,
        "tls_version": "TLSv1.2",
        "via": null
    },
    "type": "http"
}
}