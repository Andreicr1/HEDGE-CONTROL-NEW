sap.ui.define([], function () {
  "use strict";

  var API_BASE_URL = "/api/v1";

  var buildUrl = function (path) {
    if (!path) {
      return API_BASE_URL;
    }
    return path.indexOf("/") === 0 ? API_BASE_URL + path : API_BASE_URL + "/" + path;
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