let assert = require('assert');
let BrowserUpMitmProxyClient = require("browserup-mitmproxy-client");

describe('Test Browserup Mitm Proxy client', function() {
  let apiClient = new BrowserUpMitmProxyClient.BrowserUpProxyApi()

  it('should call healthcheck successfully', function() {
    let callback = function (error, data, response) {
      assert.equal(error, null);
    };
    apiClient.healthcheck(callback)
  });

  describe('add counter', function() {
    let counter = new BrowserUpMitmProxyClient.Counter();
    counter.name = 'Some counter name'
    counter.value = 3.14

    it('should add counter successfully', function() {
      let callback = function (error, data, response) {
        assert.equal(error, null);
      };
      apiClient.addCounter(counter, callback)
    });

    it('should get har log successfully with added counter', function() {
      var callback = function (error, data, response) {
        assert.equal(error, null);

        assert(data.log.pages[0])
        assert(data.log.pages[0]._counters)
        assert(data.log.pages[0]._counters.filter((c) => {
          return c.name === counter.name
        }).length > 0)
      };
      apiClient.getHarLog(callback)
    });
  });
});
