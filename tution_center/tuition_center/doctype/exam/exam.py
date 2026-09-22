# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime


class Exam(Document):
    def validate(self):
        self.validate_dates()
        self.check_clashes()

    def validate_dates(self):
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            frappe.throw(_("End time must be after start time"))

    def check_clashes(self):
        """Warn if room or batch already has an exam in overlapping window."""
        if not (self.exam_date and self.start_time and self.end_time):
            return

        filters = {
            "exam_date": self.exam_date,
            "name": ("!=", self.name),
            "status": ("!=", "Cancelled"),
        }
        if self.batch:
            filters["batch"] = self.batch
        clashes = frappe.get_all(
            "Exam",
            filters=filters,
            fields=["name", "start_time", "end_time", "room"],
        )
        for c in clashes:
            overlap = c.start_time and c.end_time and not (
                c.end_time <= self.start_time or c.start_time >= self.end_time
            )
            if overlap and self.room and c.room == self.room:
                frappe.msgprint(
                    _("Room {0} already booked for exam {1} in this slot").format(
                        self.room, c.name
                    )
                )
            elif overlap and self.batch and c.batch == self.batch:
                frappe.msgprint(_("Batch already has exam {0} in this slot").format(c.name))

    @frappe.whitelist()
    def load_students(self):
        """Pull batch students into the results grid."""
        self.set("results", [])
        students = frappe.get_all(
            "Batch Student",
            filters={"parent": self.batch, "parenttype": "Batch", "active": 1},
            fields=["student", "student_name"],
            order_by="idx",
        )
        for s in students:
            self.append(
                "results",
                {"student": s.student, "student_name": s.student_name, "marks": 0},
            )

    def validate_results(self):
        for row in self.get("results", []):
            if flt(row.marks) > flt(self.max_marks):
                frappe.throw(
                    _("Row {0}: marks exceed max marks {1}").format(row.idx, self.max_marks)
                )

    def update_result_status(self):
        for row in self.get("results", []):
            row.result = "Pass" if flt(row.marks) >= flt(self.passing_marks) else "Fail"

    def on_update(self):
        if self.get("results"):
            self.update_result_status()
