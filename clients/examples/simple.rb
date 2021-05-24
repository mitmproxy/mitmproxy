require 'bundler/inline'

gemfile do
  source 'https://rubygems.org'
  gem 'browserup_proxy_client', path: '/Users/ebeland/apps/mitmproxynew/clients/ruby'
  gem 'webdrivers', require: true
end

include BrowserupProxy
# start the proxy
#pid = Kernel.spawn("python /Users/ebeland/apps/mitmproxynew/mitmproxy/tools/browserup_proxy.py")
#Process.detach(pid)

proxy = Selenium::WebDriver::Proxy.new(http: "localhost:8080")
caps = Selenium::WebDriver::Remote::Capabilities.chrome(:proxy => proxy)
driver = Selenium::WebDriver.for :chrome, desired_capabilities: caps

driver.navigate.to "https://www.yahoo.com"
criteria = MatchCriteria.new({ 'content' => 'vaccine'})
bp = BrowserUpProxyApi.new()
sleep(3)
driver.quit
result = bp.verify_present("CheckTitle", criteria).result
puts "Content present: #{result.inspect}"


Process.kill(pid)