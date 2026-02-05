sap.ui.define([], function () {
  "use strict";

  var parse = function (text) {
    var trimmed = (text || "").trim();
    if (!trimmed) {
      return undefined;
    }
    return JSON.parse(trimmed);
  };

  var pretty = function (value) {
    if (value === undefined) {
      return "";
    }
    if (typeof value === "string") {
      return value;
    }
    try {
      return JSON.stringify(value, null, 2);
    } catch (e) {
      return String(value);
    }
  };

  return {
    parse: parse,
    pretty: pretty
  };
});
