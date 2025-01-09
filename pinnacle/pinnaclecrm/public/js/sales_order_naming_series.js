frappe.ui.form.on("Sales Order", {
	onload: function (frm) {
		if (frm.is_new()) {
			// Set custom naming series options
			frm.set_df_property("naming_series", "options", [
				"SAL-ORD-API-.FY.-",
				"SAL-ORD-MGC-.FY.-",
				"SAL-ORD-DSC-.FY.-",
				"SAL-ORD-.FY.-",
			]);
		}
	},
});
