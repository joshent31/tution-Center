# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class Teacher(Document):
    def validate(self):
        if not self.joining_date:
            self.joining_date = nowdate()

    def on_update(self):
        self.update_stats()

    def update_stats(self):
        batches = frappe.get_all(
            "Batch", filters={"teacher": self.name}, pluck="name"
        )
        self.db_set("total_batches", len(batches))
        if batches:
            count = frappe.db.count(
                "Batch Student", {"parent": ("in", batches), "parenttype": "Batch"}
            )
            self.db_set("total_students", count)

    def create_user(self, password=None):
        """Create a portal user for this teacher and link it."""
        if self.user or not self.email:
            return
        if frappe.db.exists("User", self.email):
            user = frappe.get_doc("User", self.email)
        else:
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.email,
                    "first_name": self.teacher_name,
                    "send_welcome_email": 0,
                    "user_type": "System User",
                    "roles": [{"role": "Tuition Teacher"}],
                }
            ).insert(ignore_permissions=True)
        self.db_set("user", user.name)
