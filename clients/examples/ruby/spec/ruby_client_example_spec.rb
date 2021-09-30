require 'browserup_mitmproxy_client'

RSpec.describe "RubyClientExample" do
  describe "Browserup MitmProxy client" do
    context "with initialized client" do
      api_instance = BrowserupMitmProxy::BrowserUpProxyApi.new
      counter = BrowserupMitmProxy::Counter.new({value: 3.56, name: 'name_example'})

      before(:all) do
        api_instance.reset_har_log
      end

      it "performs healthcheck" do
        api_instance.healthcheck
      end

      it "adds counter" do
        begin
          api_instance.add_counter(counter)
        rescue BrowserupMitmProxy::ApiError => e
          puts "Exception when calling BrowserUpProxyApi->add_counter: #{e}"
          raise e
        end
      end

      it "checks counter has been added" do
        expect(api_instance.get_har_log.log.pages.first._counters.count do |c|
          c.value == counter.value and c.name == c.name
        end).to be(1)
      end
    end
  end
end
