// Copyright (c) 2026, Joshent and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("New Batch"), () => {
			frappe.model.with_doctype("Batch", () => {
				const doc = frappe.model.get_new_doc("Batch");
				doc.course = frm.doc.name;
				frappe.set_route("Form", "Batch", doc.name);
			});
		});
	},
});
