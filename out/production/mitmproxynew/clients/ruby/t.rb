require_relative 'lib/browserup_proxy_client'

include BrowserupProxy

bu = BrowserUpProxyApi.new
mc = MatchCriteria.new(content_type: 'application/json')
res = bu.verify_not_present(mc).result

assert(bu.verify_present(mc).result)
