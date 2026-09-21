# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime, nowdate


class Complaint(Document):
    def validate(self):
        if not self.date_raised:
            self.date_raised = nowdate()
        if not self.raised_by:
            self.raised_by = frappe.session.user

        if self.status in ("Resolved", "Closed") and not self.resolved_on:
            self.resolved_on = now_datetime()

        if not self.due_date:
            days = 1 if self.priority in ("High", "Critical") else 3
            self.due_date = add_days(self.date_raised, days)

    def on_update(self):
        if self.status in ("Resolved", "Closed"):
            self.notify_complainant()

    def notify_complainant(self):
        if not self.raised_by:
            return
        frappe.sendmail(
            recipients=[self.raised_by],
            subject=_("Your complaint {0} has been {1}").format(self.name, self.status),
            message=_(
                "<p>Dear {0},</p><p>Your complaint <b>{1}</b> has been marked as "
                "<b>{2}</b>.</p><p>{3}</p>"
            ).format(
                self.complainant_name, self.subject, self.status, self.resolution_details or ""
            ),
            reference_doctype=self.doctype,
            reference_name=self.name,
        )

    @frappe.whitelist()
    def escalate(self):
        """Escalate: bump priority and notify managers."""
        priorities = ["Low", "Medium", "High", "Critical"]
        idx = priorities.index(self.priority) if self.priority in priorities else 1
        if idx < len(priorities) - 1:
            self.priority = priorities[idx + 1]
        self.status = "Reopened"
        self.save()
        frappe.msgprint(_("Complaint escalated to {0}").format(self.priority))
