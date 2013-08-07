/**
 * Check for updates of HoneyProxy
 */
define([ "dojo/request" ], function(request) {
	return function() {
		if (localStorage.getItem("HoneyProxyNoUpdateCheck") != "true"){
			console.log("Checking for updates...\n"+
		  	"To suppress update checks, run localStorage.setItem(\"HoneyProxyNoUpdateCheck\",true); in your JS console.");
			return request.get("http://honeyproxy.org/version.json", {
				handleAs: "json"
			})
				.then(
					function(data) {
						
						var release = "stable";
						var releaseId = 1; //change in /web/version.json, /gui/HoneyProxy/util/versionCheck.js and /libhproxy/version.py
						
						var currentReleaseId = data[release].releaseId;
						
						if (currentReleaseId > releaseId
							&& currentReleaseId > (localStorage
								.getItem("HoneyProxyReleaseId") || 0)) {
							var msg = "Update Notice: Version " + data[release].version
								+ " is available.\nOpen download page?\n\nRelease Notes:\n"
								+ data[release].message;
							if (window.confirm(msg)) {
								//Go directly to GitHub in case honeyproxy.org got compromised and serves a fake update message.
								//This way, an attacker would need to compromise both our GitHub account and honeyproxy.org
								window.open("https://github.com/mhils/HoneyProxy", '_blank');
								window.focus();
							}
						}
						localStorage.setItem("HoneyProxyReleaseId", currentReleaseId);
						
					});
		}
		return false;
	};
});