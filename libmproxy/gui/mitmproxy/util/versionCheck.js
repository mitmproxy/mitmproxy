/**
 * Check for updates of mitmproxy
 */
define([ "dojo/request" ], function(request) {
	return function() {
		if (localStorage.getItem("MitmproxyNoUpdateCheck") != "true"){
			console.log("Checking for updates...\n"+
		  	"To suppress update checks, run localStorage.setItem(\"MitmproxyNoUpdateCheck\",true); in your JS console.");
			return request.get("http://honeyproxy.org/version.json", {
				handleAs: "json"
			})
				.then(
					function(data) {
						
						var release = "stable";
						var releaseId = 1; //change in /web/version.json, /gui/mitmproxy/util/versionCheck.js and /libmproxy/version.py
						
						var currentReleaseId = data[release].releaseId;
						
						if (currentReleaseId > releaseId
							&& currentReleaseId > (localStorage
								.getItem("MitmproxyReleaseId") || 0)) {
							var msg = "Update Notice: Version " + data[release].version
								+ " is available.\nOpen download page?\n\nRelease Notes:\n"
								+ data[release].message;
							if (window.confirm(msg)) {
								//Go directly to GitHub in case honeyproxy.org got compromised and serves a fake update message.
								//This way, an attacker would need to compromise both our GitHub account and honeyproxy.org
								window.open("https://github.com/mitmproxy/mitmproxy", '_blank');
								window.focus();
							}
						}
						localStorage.setItem("MitmproxyReleaseId", currentReleaseId);
						
					});
		}
		return false;
	};
});