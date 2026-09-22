// Copyright (c) 2026, Joshent and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Tool", {
	refresh(frm) {
		frm.add_custom_button(__("Load Students"), () => {
			frm.call("load_students").then(() => frm.refresh_fields());
		});
		frm.add_custom_button(__("Mark All Present"), () => {
			(frm.doc.students || []).forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, "status", "Present");
			});
		});
		frm.add_custom_button(__("Mark All Absent"), () => {
			(frm.doc.students || []).forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, "status", "Absent");
			});
		});
	},
	batch(frm) {
		if (frm.doc.batch) {
			frm.call("load_students").then(() => frm.refresh_fields());
		}
	},
});

frappe.ui.form.on("Attendance Tool Student", {
	student(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.student && !row.student_name) {
			frappe.db.get_value("Student", row.student, "student_name", (v) => {
				frappe.model.set_value(cdt, cdn, "student_name", v.student_name);
			});
		}
	},
});
