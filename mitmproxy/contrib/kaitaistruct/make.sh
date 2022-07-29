#!/usr/bin/env bash

set -e

wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/exif.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/gif.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/jpeg.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/png.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/image/ico.ksy
wget -N -P common/ https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/common/vlq_base128_le.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/serialization/google_protobuf.ksy
wget -N https://raw.githubusercontent.com/kaitai-io/kaitai_struct_formats/master/network/tls_client_hello.ksy

kaitai-struct-compiler --target python --opaque-types=true -I . --python-package . ./*.ksy
