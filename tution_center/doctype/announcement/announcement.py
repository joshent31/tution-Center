# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class Announcement(Document):
    def validate(self):
        if not self.publish_date:
            self.publish_date = nowdate()

    def on_submit(self):
        self.send_email_broadcast()

    def get_recipients(self):
        """Resolve audience into a list of emails."""
        emails = []

        if self.audience == "Teachers":
            emails = frappe.get_all("Teacher", filters={"status": "Active"}, pluck="email")
        else:
            student_filters = {}
            if self.audience == "Batch" and self.batch:
                batch_students = frappe.get_all(
                    "Batch Student",
                    filters={"parent": self.batch, "parenttype": "Batch", "active": 1},
                    pluck="student",
                )
                student_filters["name"] = ("in", batch_students or [""])
            elif self.audience == "Course" and self.course:
                batches = frappe.get_all("Batch", filters={"course": self.course}, pluck="name")
                batch_students = frappe.get_all(
                    "Batch Student",
                    filters={"parent": ("in", batches or [""]), "parenttype": "Batch"},
                    pluck="student",
                )
                student_filters["name"] = ("in", batch_students or [""])

            student_filters["status"] = "Active"
            emails = frappe.get_all(
                "Student", filters=student_filters, pluck="student_email_id"
            )

        return [e for e in emails if e]

    def send_email_broadcast(self):
        recipients = self.get_recipients()
        if not recipients:
            return

        frappe.sendmail(
            recipients=recipients,
            subject=self.title,
            message=self.message,
            reference_doctype=self.doctype,
            reference_name=self.name,
        )
        self.db_set("sent_email", 1)
        frappe.msgprint(_("Announcement emailed to {0} recipients").format(len(recipients)))
