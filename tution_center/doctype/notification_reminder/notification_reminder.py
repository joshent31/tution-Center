# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today


class NotificationReminder(Document):
    @frappe.whitelist()
    def send_now(self):
        """Send this reminder to the resolved audience."""
        students = self.get_students()
        sent = 0

        use_email = self.channel in ("Email", "Email + SMS")
        use_sms = self.channel in ("SMS", "Email + SMS")

        for s in students:
            message = self.message
            if s.get("student_name"):
                message = message.replace("{student_name}", s.student_name)

            if use_email and s.get("student_email_id"):
                frappe.sendmail(
                    recipients=[s.student_email_id],
                    subject=self.title,
                    message=message,
                    reference_doctype=self.doctype,
                    reference_name=self.name,
                )
                sent += 1

            if use_sms and s.get("student_mobile_number"):
                try:
                    from frappe.core.doctype.sms_settings.sms_settings import send_sms

                    send_sms([s.student_mobile_number], message)
                    sent += 1
                except Exception:
                    frappe.log_error(
                        title="SMS failed", message=frappe.get_traceback()
                    )

        self.db_set("sent_count", sent)
        self.db_set("last_sent_on", now_datetime())
        self.db_set("status", "Sent")
        frappe.msgprint(_("Reminder sent to {0} recipients").format(sent))

    def get_students(self):
        filters = {"status": "Active"}
        if self.audience == "Batch" and self.batch:
            batch_students = frappe.get_all(
                "Batch Student",
                filters={"parent": self.batch, "parenttype": "Batch", "active": 1},
                pluck="student",
            )
            filters["name"] = ("in", batch_students or [""])

        return frappe.get_all(
            "Student",
            filters=filters,
            fields=["name", "student_name", "student_email_id", "student_mobile_number"],
        )
