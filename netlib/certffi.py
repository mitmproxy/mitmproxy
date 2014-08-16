from __future__ import (absolute_import, print_function, division)
import cffi
import OpenSSL

xffi = cffi.FFI()
xffi.cdef("""
    struct rsa_meth_st {
            int flags;
            ...;
    };
    struct rsa_st {
            int pad;
            long version;
            struct rsa_meth_st *meth;
            ...;
    };
""")
xffi.verify(
    """#include <openssl/rsa.h>""",
    extra_compile_args=['-w']
)


def handle(privkey):
    new = xffi.new("struct rsa_st*")
    newbuf = xffi.buffer(new)
    rsa = OpenSSL.SSL._lib.EVP_PKEY_get1_RSA(privkey._pkey)
    oldbuf = OpenSSL.SSL._ffi.buffer(rsa)
    newbuf[:] = oldbuf[:]
    return new


def set_flags(privkey, val):
    hdl = handle(privkey)
    hdl.meth.flags = val
    return privkey


def get_flags(privkey):
    hdl = handle(privkey)
    return hdl.meth.flags
