frappe.ui.form.on("Lead", {
	onload: function (frm) {
		if (frm.is_new()) {
			// Set custom naming series options
			frm.set_df_property("naming_series", "options", [
				"CRM-LEAD-API-.FY.-",
				"CRM-LEAD-MGC-.FY.-",
				"CRM-LEAD-DSC-.FY.-",
				"CRM-LEAD-.FY.-",
			]);
		}
	},
	before_save: function (frm) {
		// Automatically compute and set financial year in YY-YY format
		let currentYear = frappe.datetime.get_today().split("-")[0];
		let nextYear = (parseInt(currentYear) + 1).toString().slice(-2);
		let financialYear = `${currentYear.slice(-2)}-${nextYear}`;

		if (frm.doc.naming_series.includes("API")) {
			frm.set_value("naming_series", `CRM-LEAD-API-${financialYear}-`);
		} else if (frm.doc.naming_series.includes("MGC")) {
			frm.set_value("naming_series", `CRM-LEAD-MGC-${financialYear}-`);
		} else if (frm.doc.naming_series.includes("DSC")) {
			frm.set_value("naming_series", `CRM-LEAD-DSC-${financialYear}-`);
		} else {
			frm.set_value("naming_series", `CRM-LEAD-${financialYear}-`);
		}
	},
});
