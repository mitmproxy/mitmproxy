# requires openapi-generator installed

DIR="$(dirname "${BASH_SOURCE[0]}")"  # Get the directory names
openapi-generator generate --package-name BrowserUpProxyClient -g java -i "${DIR}/../browserup-proxy.schema.json" -o java -c config-java.yaml
openapi-generator generate --package-name BrowserUpProxyClient -g javascript -i "${DIR}/../browserup-proxy.schema.json" -o javascript -c config-javascript.yaml
openapi-generator generate --package-name BrowserUpProxyClient -g python -i "${DIR}/../browserup-proxy.schema.json" -o python -c config-python.yaml
openapi-generator generate --package-name BrowserUpProxyClient -g ruby -i "${DIR}/../browserup-proxy.schema.json" -o ruby -c config-ruby.yaml