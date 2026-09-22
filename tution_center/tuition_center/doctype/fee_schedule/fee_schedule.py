# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FeeSchedule(Document):
    def validate(self):
        self.calculate_totals()

    @frappe.whitelist()
    def get_students_from_batch(self):
        """Pull active students of the selected batch into the table."""
        self.set("students", [])
        students = frappe.get_all(
            "Batch Student",
            filters={"parent": self.batch, "parenttype": "Batch", "active": 1},
            fields=["student", "student_name"],
            order_by="idx",
        )
        for s in students:
            self.append(
                "students",
                {
                    "student": s.student,
                    "student_name": s.student_name,
                    "fee_amount": frappe.db.get_value(
                        "Fee Structure", self.fee_structure, "net_amount"
                    ),
                },
            )
        self.calculate_totals()

    def calculate_totals(self):
        self.total_students = len(self.get("students", []))
        self.total_amount = sum(flt(d.fee_amount) for d in self.get("students", []))

    def on_submit(self):
        self.create_fee_enrolments()

    def create_fee_enrolments(self):
        """Create one Fee Enrolment per student (skip duplicates)."""
        created = 0
        for row in self.get("students", []):
            exists = frappe.db.exists(
                "Fee Enrolment",
                {
                    "student": row.student,
                    "fee_structure": self.fee_structure,
                    "academic_term": self.academic_term,
                    "docstatus": ("<", 2),
                },
            )
            if exists:
                continue

            frappe.get_doc(
                {
                    "doctype": "Fee Enrolment",
                    "student": row.student,
                    "student_name": row.student_name,
                    "course": self.course,
                    "batch": self.batch,
                    "academic_term": self.academic_term,
                    "fee_structure": self.fee_structure,
                    "fee_amount": flt(row.fee_amount),
                    "due_date": self.due_date,
                    "status": "Unpaid",
                }
            ).insert(ignore_permissions=True)
            created += 1

        frappe.msgprint(_("{0} Fee Enrolments created").format(created))
        return created
