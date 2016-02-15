#!/bin/sh

openssl genrsa -out client.key 2048
openssl req -key client.key -new -out client.req
openssl x509 -req -days 365 -in client.req -signkey client.key -out client.crt -extfile client.cnf -extensions ssl_client
openssl x509 -req -days 1000 -in client.req -CA ~/.mitmproxy/mitmproxy-ca.pem -CAkey ~/.mitmproxy/mitmproxy-ca.pem -set_serial 00001 -out client.crt -extensions ssl_client
cat client.key client.crt > client.pem
openssl x509 -text -noout -in client.pem
