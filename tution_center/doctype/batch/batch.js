// Copyright (c) 2026, Joshent and contributors
// For license information, please see license.txt

frappe.ui.form.on("Batch", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Mark Attendance"), () => {
			frappe.model.with_doctype("Attendance Tool", () => {
				const doc = frappe.model.get_new_doc("Attendance Tool");
				doc.batch = frm.doc.name;
				doc.date = frappe.datetime.get_today();
				frappe.set_route("Form", "Attendance Tool", doc.name);
			});
		});

		frm.add_custom_button(__("Generate Fee Schedule"), () => {
			frappe.model.with_doctype("Fee Schedule", () => {
				const doc = frappe.model.get_new_doc("Fee Schedule");
				doc.batch = frm.doc.name;
				doc.course = frm.doc.course;
				frappe.set_route("Form", "Fee Schedule", doc.name);
			});
		});
	},
});

frappe.ui.form.on("Batch Student", {
	student(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.student) {
			frappe.db.get_value("Student", row.student, "student_name", (v) => {
				frappe.model.set_value(cdt, cdn, "student_name", v.student_name);
			});
		}
	},
});
