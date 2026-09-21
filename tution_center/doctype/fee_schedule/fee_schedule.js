// Copyright (c) 2026, Joshent and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Schedule", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Students from Batch"), () => {
				frm.call("get_students_from_batch").then(() => frm.refresh_fields());
			});
		}
	},
});

frappe.ui.form.on("Fee Schedule Student", {
	student(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.student && !row.student_name) {
			frappe.db.get_value("Student", row.student, "student_name", (v) => {
				frappe.model.set_value(cdt, cdn, "student_name", v.student_name);
			});
		}
	},
});
