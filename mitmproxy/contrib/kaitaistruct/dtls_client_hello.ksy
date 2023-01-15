meta:
  id: dtls_client_hello
  endian: be
  license: MIT

seq:
  - id: version
    type: version

  - id: random
    type: random

  - id: session_id
    type: session_id

  - id: cookie
    type: cookie

  - id: cipher_suites
    type: cipher_suites

  - id: compression_methods
    type: compression_methods

  - id: extensions
    type: extensions
    if: _io.eof == false

types:
  version:
    seq:
      - id: major
        type: u1

      - id: minor
        type: u1

  random:
    seq:
      - id: gmt_unix_time
        type: u4

      - id: random
        size: 28

  session_id:
    seq:
      - id: len
        type: u1

      - id: sid
        size: len

  cookie:
    seq:
      - id: len
        type: u1

      - id: cookie
        size: len

  cipher_suites:
    seq:
      - id: len
        type: u2

      - id: cipher_suites
        type: u2
        repeat: expr
        repeat-expr: len/2

  compression_methods:
    seq:
      - id: len
        type: u1

      - id: compression_methods
        size: len

  extensions:
    seq:
      - id: len
        type: u2

      - id: extensions
        type: extension
        repeat: eos

  extension:
    seq:
      - id: type
        type: u2

      - id: len
        type: u2

      - id: body
        size: len
        type:
          switch-on: type
          cases:
            0: sni
            16: alpn

  sni:
    seq:
      - id: list_length
        type: u2

      - id: server_names
        type: server_name
        repeat: eos

  server_name:
    seq:
      - id: name_type
        type: u1

      - id: length
        type: u2

      - id: host_name
        size: length

  alpn:
    seq:
      - id: ext_len
        type: u2

      - id: alpn_protocols
        type: protocol
        repeat: eos

  protocol:
    seq:
      - id: strlen
        type: u1

      - id: name
        size: strlen
