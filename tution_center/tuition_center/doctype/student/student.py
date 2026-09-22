# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class Student(Document):
    def autoname(self):
        pass

    def validate(self):
        if not self.joining_date:
            self.joining_date = nowdate()

    def on_update(self):
        self.update_stats()

    def update_stats(self):
        batches = frappe.get_all(
            "Batch Student",
            filters={"student": self.name, "parenttype": "Batch", "active": 1},
            pluck="parent",
        )
        self.db_set("total_batches", len(set(batches)))

        due = frappe.db.sql(
            """select sum(fee_amount - paid_amount) from `tabFee Enrolment`
               where student = %s and status in ('Unpaid', 'Partially Paid')""",
            (self.name,),
        )[0][0]
        self.db_set("total_fees_due", due or 0)

    @frappe.whitelist()
    def create_portal_user(self):
        """Create a portal (Website User) account for the student."""
        if self.user:
            frappe.msgprint("Student already linked to a user")
            return self.user
        if not self.student_email_id:
            frappe.throw("Email required to create a portal user")

        if frappe.db.exists("User", self.student_email_id):
            user = frappe.get_doc("User", self.student_email_id)
        else:
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.student_email_id,
                    "first_name": self.student_name,
                    "send_welcome_email": 0,
                    "user_type": "Website User",
                    "roles": [{"role": "Student"}, {"role": "Guardian"}],
                }
            ).insert(ignore_permissions=True)
        self.db_set("user", user.name)
        frappe.msgprint(f"Portal user {user.name} linked")
        return user.name

    @frappe.whitelist()
    def enroll_in_batch(self, batch):
        """Enroll this student into the given batch."""
        batch_doc = frappe.get_doc("Batch", batch)
        return batch_doc.enroll_students([self.name])
