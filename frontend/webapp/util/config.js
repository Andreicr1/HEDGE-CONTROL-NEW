sap.ui.define([], function () {
	"use strict";

	// Replaced at deploy time by GitHub Actions (SWA workflow)
	var sApiBaseUrl = "__HC_API_BASE_URL__";

	// Auto-detect environment when the placeholder is unreplaced.
	if (sApiBaseUrl === "__HC_API" + "_BASE_URL__" && typeof window !== "undefined" && window.location) {
		var h = window.location.hostname || "";
		if (/\.azurestaticapps\.net$/i.test(h)) {
			// Azure SWA with Linked Backend — same-origin proxy via /api
			sApiBaseUrl = "/api";
		} else if (h === "localhost" || h === "127.0.0.1") {
			sApiBaseUrl = "http://localhost:8000";
		}
	}

	return {
		getApiBaseUrl: function () {
			return sApiBaseUrl;
		}
	};
});

