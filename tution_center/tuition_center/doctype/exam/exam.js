// Copyright (c) 2026, Joshent and contributors
// For license information, please see license.txt

frappe.ui.form.on("Exam", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Load Batch Students"), () => {
				frm.call("load_students").then(() => frm.refresh_fields());
			});
		}
	},
});

frappe.ui.form.on("Exam Result Student", {
	marks(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (frm.doc.max_marks && row.marks > frm.doc.max_marks) {
			frappe.msgprint(__("Marks cannot exceed max marks"));
		}
	},
});
