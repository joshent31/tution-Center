# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, nowdate


class Batch(Document):
    def validate(self):
        self.validate_dates()
        self.validate_capacity()

    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            frappe.throw(_("End Date cannot be before Start Date"))

    def validate_capacity(self):
        if self.max_seats and len(self.get("students", [])) > self.max_seats:
            frappe.throw(
                _("Cannot enroll more than {0} students in this batch").format(self.max_seats)
            )

    def on_update(self):
        self.update_fill_rate()

    def update_fill_rate(self):
        enrolled = len(self.get("students", [])) or frappe.db.count(
            "Batch Student", {"parent": self.name, "parenttype": "Batch"}
        )
        if self.max_seats:
            self.db_set("filled_percentage", flt(enrolled) / self.max_seats * 100)

    @frappe.whitelist()
    def enroll_students(self, students):
        """Bulk enroll students into this batch."""
        import json

        if isinstance(students, str):
            students = json.loads(students)

        existing = {d.student for d in self.get("students", [])}
        added = 0
        for student in students:
            if student in existing:
                continue
            student_name = frappe.db.get_value("Student", student, "student_name")
            self.append(
                "students",
                {
                    "student": student,
                    "student_name": student_name,
                    "enrollment_date": nowdate(),
                    "active": 1,
                    "course": self.course,
                },
            )
            added += 1
        self.save()
        return added
