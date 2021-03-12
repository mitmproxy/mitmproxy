# Updating the clients

The commands below re-generate each API client.  Importantly, we don't want to just
accept everything that is spit out if we re-generate a client. The tests in the 
generated clients are just stubs. We may be maintaining other changes in the code we
also want to keep. The way to integrate is to review what the generator proposes as a
PR and keep and reject what we want.

The  API spec is auto-updated everytime the API is launched
It lives in the top-level folder as: browserup-proxy.schema.json

The schema is assembled by browserup_addons_manager.py when it loads
addons. The addons declare their schema and falcon routes, which are used to 
build the OpenAPI spec.

# Installing the open-api generator:
`brew install openapi-generator`

for instructions via NPM, or a Jar here:

https://openapi-generator.tech/docs/installation/

## Config
We have language specific config files set. The options for every language are
different. So see them, follow this pattern:

`openapi-generator config-help -g python`


# Generating Clients

## Java
`openapi-generator generate --package-name BrowserUpProxyClient  -g java -i /Users/ebeland/apps/mitmproxynew/browserup-proxy.schema.json -o java -c config-java.yaml`

## JavaScript
`openapi-generator generate --package-name BrowserUpProxyClient  -g javascript -i /Users/ebeland/apps/mitmproxynew/browserup-proxy.schema.json -o javascript -c config-javascript.yaml`

## Ruby
`openapi-generator generate --package-name BrowserUpProxyClient  -g ruby -i /Users/ebeland/apps/mitmproxynew/browserup-proxy.schema.json -o ruby -c config-ruby.yaml`

## Python
`openapi-generator generate --package-name BrowserUpProxyClient  -g python -i /Users/ebeland/apps/mitmproxynew/browserup-proxy.schema.json -o python -c config-python.yaml`


Notes:
The specs need updating and aren't real out of the box!  Other changes may be necessary!