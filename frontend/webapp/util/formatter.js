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
			if (s === "active" || s === "awarded" || s === "settled" || s === "completed" || s === "approved" || s === "clear" || s === "fully_hedged") {
				return "Success";
			}
			if (s === "pending" || s === "open" || s === "draft" || s === "created" || s === "flagged" || s === "partially_hedged") {
				return "Warning";
			}
			if (s === "rejected" || s === "cancelled" || s === "error" || s === "failed" || s === "archived" || s === "expired" || s === "blocked") {
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
		},

		/**
		 * Map counterparty type enum to display label.
		 * @param {string} sType – broker | bank_br
		 * @returns {string}
		 */
		counterpartyType: function (sType) {
			var mTypes = { broker: "Corretora", bank_br: "Banco BR" };
			return mTypes[sType] || sType || "";
		},

		/**
		 * Map hedge classification to Portuguese label.
		 * long → Compra, short → Venda
		 * @param {string} sClassification
		 * @returns {string}
		 */
		classificationText: function (sClassification) {
			if (!sClassification) { return ""; }
			var mMap = { long: "Compra", short: "Venda" };
			return mMap[sClassification] || sClassification;
		},

		/**
		 * Map hedge classification to semantic state.
		 * long (Compra) → Success, short (Venda) → Warning
		 * @param {string} sClassification
		 * @returns {string}
		 */
		classificationState: function (sClassification) {
			if (!sClassification) { return "None"; }
			return sClassification === "long" ? "Success" : "Warning";
		},

		/**
		 * Map float_pricing_convention code to human-readable label.
		 * avg → Média Mensal, avginter → Média Inter-Mês, c2r → Cash-to-Reference
		 * @param {string} sConvention
		 * @returns {string}
		 */
		floatPricingText: function (sConvention) {
			if (!sConvention) { return "—"; }
			var mMap = {
				avg: "Média Mensal",
				avginter: "Média Inter-Mês",
				c2r: "Cash-to-Reference"
			};
			return mMap[sConvention] || sConvention;
		},

		/**
		 * Build the verification period description based on float_pricing_convention.
		 * avg → "Mês/Ano: MM/YYYY"
		 * c2r → "Fixing: dd/mm/yyyy"
		 * avginter → "Dias: N"
		 * @param {string} sConvention
		 * @param {number} iMonth
		 * @param {number} iYear
		 * @param {string} sFixingDate - ISO date
		 * @param {number} iDays
		 * @returns {string}
		 */
		verificationPeriodText: function (sConvention, iMonth, iYear, sFixingDate, iDays) {
			if (!sConvention) { return ""; }
			if (sConvention === "avg") {
				if (iMonth && iYear) {
					var sMonth = String(iMonth).padStart(2, "0");
					return "Mês/Ano: " + sMonth + "/" + iYear;
				}
				return "";
			}
			if (sConvention === "c2r") {
				if (sFixingDate) {
					try {
						var oDate = new Date(sFixingDate);
						if (!isNaN(oDate.getTime())) {
							return "Fixing: " + oDate.toLocaleDateString("pt-BR");
						}
					} catch (e) { /* ignore */ }
					return "Fixing: " + sFixingDate;
				}
				return "";
			}
			if (sConvention === "avginter") {
				if (iDays) {
					return "Dias para cômputo: " + iDays;
				}
				return "";
			}
			return "";
		},

		/**
		 * Map DealLinkedType to Portuguese label.
		 */
		dealLinkedTypeText: function (sType) {
			var mMap = {
				sales_order: "Ordem de Venda (SO)",
				purchase_order: "Ordem de Compra (PO)",
				hedge: "Contrato de Hedge",
				contract: "Contrato"
			};
			return mMap[sType] || sType || "";
		},

		/**
		 * Format hedge_ratio (0-1 float) as percentage string.
		 */
		percentDisplay: function (fValue) {
			if (fValue == null) { return ""; }
			return (parseFloat(fValue) * 100).toFixed(1) + " %";
		},

		/**
		 * Map exposure source_type to Portuguese label.
		 * purchase_order → Exposição Passiva (PO)
		 * sales_order → Exposição Ativa (SO)
		 * @param {string} sSourceType
		 * @returns {string}
		 */
		exposureTypeLabel: function (sSourceType) {
			if (!sSourceType) { return ""; }
			var mMap = {
				purchase_order: "Exposição Passiva (PO)",
				sales_order: "Exposição Ativa (SO)"
			};
			return mMap[sSourceType] || sSourceType;
		},

		/**
		 * Map exposure source_type to semantic state.
		 * purchase_order (Passiva) → Warning, sales_order (Ativa) → Success
		 * @param {string} sSourceType
		 * @returns {string}
		 */
		exposureTypeState: function (sSourceType) {
			if (!sSourceType) { return "None"; }
			return sSourceType === "sales_order" ? "Success" : "Warning";
		},

		/**
		 * Map price_type to Portuguese label.
		 * fixed → Fixo, variable → Variável
		 * @param {string} sPriceType
		 * @returns {string}
		 */
		priceTypeLabel: function (sPriceType) {
			if (!sPriceType) { return "—"; }
			var mMap = { fixed: "Fixo", variable: "Variável" };
			return mMap[sPriceType] || sPriceType;
		},

		/**
		 * Format settlement_month (YYYY-MM) to "MMM/YYYY" display.
		 * @param {string} sMonth – e.g. "2025-03"
		 * @returns {string}
		 */
		settlementMonthDisplay: function (sMonth) {
			if (!sMonth) { return "—"; }
			var aParts = sMonth.split("-");
			if (aParts.length < 2) { return sMonth; }
			var aMonths = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
			var iMonth = parseInt(aParts[1], 10);
			if (isNaN(iMonth) || iMonth < 1 || iMonth > 12) { return sMonth; }
			return aMonths[iMonth - 1] + "/" + aParts[0];
		},

		/**
		 * Map commercial exposure source_type to direction label.
		 * sales_order → Ativa, purchase_order → Passiva
		 * @param {string} sSourceType
		 * @returns {string}
		 */
		exposureDirectionLabel: function (sSourceType) {
			if (!sSourceType) { return ""; }
			var mMap = {
				sales_order: "Ativa",
				purchase_order: "Passiva"
			};
			return mMap[sSourceType] || sSourceType;
		},

		/**
		 * Map commercial exposure source_type to semantic state.
		 * sales_order (Ativa) → Error (short), purchase_order (Passiva) → Success (long)
		 * @param {string} sSourceType
		 * @returns {string}
		 */
		exposureDirectionState: function (sSourceType) {
			if (!sSourceType) { return "None"; }
			return sSourceType === "purchase_order" ? "Success" : "Error";
		},

		/**
		 * Compute settlement display value based on pricing convention.
		 * AVG → reference_month, AVGInter → observation period, C2R → fixing_date
		 * @param {string} sPricingConvention
		 * @param {string} sReferenceMonth
		 * @param {string} sObsStart
		 * @param {string} sObsEnd
		 * @param {string} sFixingDate
		 * @param {string} sSettlementMonth - fallback
		 * @returns {string}
		 */
		exposureSettlementValue: function (sPricingConvention, sReferenceMonth, sObsStart, sObsEnd, sFixingDate, sSettlementMonth) {
			var _fmtMonth = function (sMonth) {
				if (!sMonth) { return "—"; }
				var aParts = sMonth.split("-");
				if (aParts.length < 2) { return sMonth; }
				var aMonths = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
				var iMonth = parseInt(aParts[1], 10);
				if (isNaN(iMonth) || iMonth < 1 || iMonth > 12) { return sMonth; }
				return aMonths[iMonth - 1] + "/" + aParts[0];
			};
			var _fmtDate = function (sDate) {
				if (!sDate) { return ""; }
				try {
					var oDate = new Date(sDate);
					if (isNaN(oDate.getTime())) { return sDate; }
					return oDate.toLocaleDateString();
				} catch (e) { return sDate; }
			};

			if (sPricingConvention === "AVG" && sReferenceMonth) {
				return _fmtMonth(sReferenceMonth);
			}
			if (sPricingConvention === "AVGInter" && (sObsStart || sObsEnd)) {
				return _fmtDate(sObsStart) + " — " + _fmtDate(sObsEnd);
			}
			if (sPricingConvention === "C2R" && sFixingDate) {
				return _fmtDate(sFixingDate);
			}
			if (sSettlementMonth) {
				return _fmtMonth(sSettlementMonth);
			}
			return "—";
		}
	};
});
