// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("TP Telnyx Settings", {
	refresh: function(frm) {
		if (frm.doc.enabled) {
			frm.add_custom_button(__("Fetch Applications"), function() {
				frappe.call({
					method: "telephony.telnyx.api.fetch_applications",
					callback: function(r) {
						if (r.message) {
							frappe.msgprint(__("Applications fetched successfully"));
							frm.reload_doc();
						}
					}
				});
			});
		}
	}
});
