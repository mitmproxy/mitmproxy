#!/bin/bash

# requires openapi-generator installed

DIR="$(dirname "${BASH_SOURCE[0]}")"

# we need to regenerate the schema in the top level dir


rm -rf java && npx openapi-generator-cli generate \
--package-name BrowserUpMitmProxyClient \
-g java -i "${DIR}/../browserup-proxy.schema.json" \
-o java -c config-java.yaml

rm -rf javascript && npx openapi-generator-cli generate \
--package-name BrowserUpMitmProxyClient \
-g javascript -i "${DIR}/../browserup-proxy.schema.json" \
-o javascript -c config-javascript.yaml

rm -rf python && npx openapi-generator-cli generate \
--package-name BrowserUpMitmProxyClient \
-g python -i "${DIR}/../browserup-proxy.schema.json" \
-o python -c config-python.yaml

rm -rf ruby && npx openapi-generator-cli generate \
--package-name BrowserUpMitmProxyClient \
-g ruby -i "${DIR}/../browserup-proxy.schema.json" \
-o ruby -c config-ruby.yaml

./post-build-java-client.sh
