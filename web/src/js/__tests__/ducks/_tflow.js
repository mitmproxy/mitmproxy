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
        "id": "4a18d1a0-50a1-48dd-9aa6-d45d74282939",
        "sni": "address",
        "ssl_established": false,
        "timestamp_end": 3.0,
        "timestamp_ssl_setup": 2.0,
        "timestamp_start": 1.0,
        "tls_version": "TLSv1.2"
    },
    "error": {
        "msg": "error",
        "timestamp": 1495370312.4814785
    },
    "id": "d91165be-ca1f-4612-88a9-c0f8696f3e29",
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
        "timestamp_end": 1495370312.4814625,
        "timestamp_start": 1495370312.481462
    },
    "server_conn": {
        "address": [
            "address",
            22
        ],
        "alpn_proto_negotiated": null,
        "id": "f087e7b2-6d0a-41a8-a8f0-e1a4761395f8",
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