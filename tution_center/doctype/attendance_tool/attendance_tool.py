# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AttendanceTool(Document):
    def validate(self):
        self.load_students_if_empty()

    @frappe.whitelist()
    def load_students(self):
        """Pull batch students into grid with default Present."""
        self.load_students_if_empty(force=True)

    def load_students_if_empty(self, force=False):
        if self.get("students") and not force:
            return
        self.set("students", [])
        rows = frappe.get_all(
            "Batch Student",
            filters={"parent": self.batch, "parenttype": "Batch", "active": 1},
            fields=["student", "student_name"],
            order_by="idx",
        )
        for r in rows:
            self.append(
                "students",
                {"student": r.student, "student_name": r.student_name, "status": "Present"},
            )

    def on_submit(self):
        """Create/overwrite Student Attendance for each row."""
        created = 0
        for row in self.get("students", []):
            existing = frappe.db.exists(
                "Student Attendance",
                {"student": row.student, "date": self.date, "batch": self.batch},
            )
            if existing:
                frappe.db.set_value(
                    "Student Attendance", existing, "status", row.status, update_modified=False
                )
            else:
                frappe.get_doc(
                    {
                        "doctype": "Student Attendance",
                        "student": row.student,
                        "student_name": row.student_name,
                        "date": self.date,
                        "batch": self.batch,
                        "status": row.status,
                    }
                ).insert(ignore_permissions=True)
                created += 1

        frappe.msgprint(_("Attendance saved for {0} students").format(created))
