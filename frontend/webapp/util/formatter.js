sap.ui.define([], function () {
	"use strict";

	return {
		/**
		 * Format ISO date string to locale display.
		 * @param {string} sDate - ISO date string
		 * @returns {string}
		 */
		dateDisplay: function (sDate) {
			if (!sDate) {
				return "";
			}
			try {
				var oDate = new Date(sDate);
				if (isNaN(oDate.getTime())) {
					return sDate;
				}
				return oDate.toLocaleDateString();
			} catch (e) {
				return sDate;
			}
		},

		/**
		 * Format ISO datetime to locale display.
		 * @param {string} sDateTime
		 * @returns {string}
		 */
		dateTimeDisplay: function (sDateTime) {
			if (!sDateTime) {
				return "";
			}
			try {
				var oDate = new Date(sDateTime);
				if (isNaN(oDate.getTime())) {
					return sDateTime;
				}
				return oDate.toLocaleString();
			} catch (e) {
				return sDateTime;
			}
		},

		/**
		 * Format a number with 2 decimal places.
		 * @param {number|string} vValue
		 * @returns {string}
		 */
		numberTwoDecimals: function (vValue) {
			if (vValue === null || vValue === undefined || vValue === "") {
				return "";
			}
			var fValue = parseFloat(vValue);
			if (isNaN(fValue)) {
				return String(vValue);
			}
			return fValue.toLocaleString(undefined, {
				minimumFractionDigits: 2,
				maximumFractionDigits: 2
			});
		},

		/**
		 * Format a number with 4 decimal places (prices).
		 * @param {number|string} vValue
		 * @returns {string}
		 */
		priceFourDecimals: function (vValue) {
			if (vValue === null || vValue === undefined || vValue === "") {
				return "";
			}
			var fValue = parseFloat(vValue);
			if (isNaN(fValue)) {
				return String(vValue);
			}
			return fValue.toLocaleString(undefined, {
				minimumFractionDigits: 4,
				maximumFractionDigits: 4
			});
		},

		/**
		 * Map status to semantic ObjectStatus state.
		 * @param {string} sStatus
		 * @returns {string} sap.ui.core.ValueState
		 */
		statusState: function (sStatus) {
			if (!sStatus) {
				return "None";
			}
			var s = sStatus.toLowerCase();
			if (s === "active" || s === "awarded" || s === "settled" || s === "completed") {
				return "Success";
			}
			if (s === "pending" || s === "open" || s === "draft" || s === "created") {
				return "Warning";
			}
			if (s === "rejected" || s === "cancelled" || s === "error" || s === "failed" || s === "archived") {
				return "Error";
			}
			return "Information";
		},

		/**
		 * Capitalize first letter.
		 * @param {string} sText
		 * @returns {string}
		 */
		capitalize: function (sText) {
			if (!sText) {
				return "";
			}
			return sText.charAt(0).toUpperCase() + sText.slice(1);
		},

		/**
		 * Truncate UUID for table display.
		 * @param {string} sUuid
		 * @returns {string}
		 */
		shortUuid: function (sUuid) {
			if (!sUuid) {
				return "";
			}
			return sUuid.length > 8 ? sUuid.substring(0, 8) + "…" : sUuid;
		},

		/**
		 * Format boolean for display.
		 * @param {boolean} bValue
		 * @returns {string}
		 */
		booleanText: function (bValue) {
			return bValue ? "Yes" : "No";
		}
	};
});
