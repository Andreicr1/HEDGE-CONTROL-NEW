sap.ui.define([], function () {
  "use strict";

  var isAbsoluteUrl = function (value) {
    return typeof value === "string" && /^https?:\/\//i.test(value);
  };

  var readConfiguredBaseUrl = function () {
    var win = typeof window !== "undefined" ? window : undefined;
    if (!win) {
      return "";
    }

    var search = win.location && win.location.search ? win.location.search : "";
    try {
      var params = new URLSearchParams(search);
      var baseFromQuery = (params.get("apiBaseUrl") || "").trim();
      if (baseFromQuery) {
        try {
          win.localStorage.setItem("hc.apiBaseUrl", baseFromQuery);
        } catch (e) {
          // ignore storage failures
        }
        return baseFromQuery;
      }
    } catch (e) {
      // ignore URLSearchParams failures
    }

    if (win.__HC_CONFIG__ && typeof win.__HC_CONFIG__.apiBaseUrl === "string") {
      var fromWindow = win.__HC_CONFIG__.apiBaseUrl.trim();
      if (fromWindow) {
        return fromWindow;
      }
    }

    try {
      var fromStorage = (win.localStorage.getItem("hc.apiBaseUrl") || "").trim();
      if (fromStorage) {
        return fromStorage;
      }
    } catch (e) {
      // ignore storage failures
    }

    return "";
  };

  var normalizeBaseUrl = function (baseUrl) {
    if (!baseUrl) {
      return "";
    }
    return baseUrl.replace(/\/$/, "");
  };

  var buildUrl = function (path) {
    if (!path) {
      return normalizeBaseUrl(readConfiguredBaseUrl());
    }
    if (isAbsoluteUrl(path)) {
      return path;
    }

    var baseUrl = normalizeBaseUrl(readConfiguredBaseUrl());

    // If we're hosted on Azure Static Web Apps and baseUrl is not configured,
    // fail deterministically with an explicit configuration message instead of
    // silently calling the static host (404/405).
    var win = typeof window !== "undefined" ? window : undefined;
    var host = win && win.location ? String(win.location.hostname || "") : "";
    if (!baseUrl && host && /\.azurestaticapps\.net$/i.test(host)) {
      var configError = new Error(
        "API base URL not configured. Append ?apiBaseUrl=https://<backend-host> once (it will be stored), or set window.__HC_CONFIG__.apiBaseUrl in index.html."
      );
      configError.status = 0;
      configError.statusText = "API_BASE_URL_NOT_CONFIGURED";
      configError.url = path;
      configError.details = {
        host: host,
        path: path
      };
      throw configError;
    }

    if (!baseUrl) {
      // Same-origin (e.g. UI served by backend)
      return path;
    }

    return path.indexOf("/") === 0 ? baseUrl + path : baseUrl + "/" + path;
  };

  var buildError = function (response, details) {
    var statusText = response.statusText || "";
    var message = "Request failed with status " + response.status + (statusText ? " " + statusText : "");
    var error = new Error(message);
    error.status = response.status;
    error.statusText = statusText;
    error.url = response.url;
    error.details = details;
    return error;
  };

  var parseJson = function (response) {
    return response
      .json()
      .catch(function () {
        return undefined;
      })
      .then(function (payload) {
        if (!response.ok) {
          throw buildError(response, payload);
        }
        return payload;
      });
  };

  var parseText = function (response) {
    return response
      .text()
      .catch(function () {
        return "";
      })
      .then(function (payload) {
        if (!response.ok) {
          throw buildError(response, payload);
        }
        return payload;
      });
  };

  var request = function (path, options) {
    return fetch(buildUrl(path), options);
  };

  return {
    getJson: function (path) {
      return request(path, {
        method: "GET",
        headers: {
          Accept: "application/json"
        }
      }).then(parseJson);
    },
    getText: function (path) {
      return request(path, {
        method: "GET",
        headers: {
          Accept: "text/plain"
        }
      }).then(parseText);
    },
    postJson: function (path, body) {
      return request(path, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
      }).then(parseJson);
    }
  };
});