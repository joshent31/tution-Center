# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class Certificate(Document):
    def validate(self):
        if not self.issue_date:
            self.issue_date = nowdate()
        if not self.content:
            self.content = self.get_default_content()

    def get_default_content(self):
        course = frappe.db.get_value("Course", self.course, "course_name") if self.course else ""
        return _(
            "This is to certify that <b>{0}</b> has successfully completed the course "
            "<b>{1}</b> at our Tuition Center."
        ).format(self.student_name or "", course or "")
