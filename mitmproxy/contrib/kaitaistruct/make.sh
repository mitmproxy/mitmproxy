#!/usr/bin/env bash

wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/exif_be.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/exif_le.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/exif.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/gif.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/jpeg.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/png.ksy
wget -N https://raw.githubusercontent.com/mitmproxy/mitmproxy/master/mitmproxy/contrib/tls_client_hello.py

kaitai-struct-compiler --target python --opaque-types=true *.ksy
