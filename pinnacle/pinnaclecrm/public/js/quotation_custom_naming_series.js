frappe.ui.form.on("Quotation", {
	onload: function (frm) {
		if (frm.is_new()) {
			// Set custom naming series options
			frm.set_df_property("naming_series", "options", [
				"SAL-QTN-API-.FY.-",
				"SAL-QTN-MGC-.FY.-",
				"SAL-QTN-DSC-.FY.-",
				"SAL-QTN-.FY.-",
			]);
		}
	},
});
