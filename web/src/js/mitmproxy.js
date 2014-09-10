
mitmproxy = function () {
	function init() {
		React.renderComponent(Router(), $("#mitmproxy")[0]);
	}
	var exports = {
		init: init,
	};
	return exports;
}();