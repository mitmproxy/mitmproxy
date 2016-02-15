#!/bin/bash

if [ ! -f ./private.key ]
then
    openssl genrsa -out private.key 3072
fi
openssl req \
    -batch \
    -new -x509 \
    -key private.key \
    -sha256 \
    -out cert.pem \
    -days 9999 \
    -config ./openssl.cnf
openssl x509 -in cert.pem -text -noout
cat ./private.key ./cert.pem > testcert.pem
rm ./private.key ./cert.pem
